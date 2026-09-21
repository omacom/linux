// SPDX-License-Identifier: GPL-2.0-only OR MIT
/* Apple USB4 DP-input bridge. Register semantics recovered from macOS 13.5. */
#include <linux/delay.h>
#include <linux/interrupt.h>
#include <linux/io.h>
#include <linux/jiffies.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/of_platform.h>
#include <linux/platform_device.h>
#include <linux/pm_runtime.h>
#include "dpin.h"

#define DPIN_HPD		0x00
#define DPIN_HPD_LEVEL		BIT(2)
#define DPIN_IRQ_STATUS		0x04
#define DPIN_IRQ_HPD_CHANGE	BIT(0)
#define DPIN_IRQ_HPD_PULSE	BIT(1)
#define DPIN_IRQ_MASK		GENMASK(1, 0)
#define DPIN_IRQ_ENABLE		0x08
#define DPIN_CONTROL		0x0c
#define DPIN_STATUS		0x10
#define DPIN_INACTIVE		BIT(0)

struct apple_dpin {
	struct device *dev;
	void __iomem *regs;
	struct mutex lock;
	int irq;
	bool leased;
	bool hpd;
	void (*notify)(void *, bool);
	void *cookie;
};

static void dpin_mask(struct apple_dpin *dpin, unsigned int reg, u32 mask, u32 value)
{
	writel((readl(dpin->regs + reg) & ~mask) | value, dpin->regs + reg);
}

static irqreturn_t apple_dpin_irq(int irq, void *data)
{
	struct apple_dpin *dpin = data;
	u32 pending, hpd, after;
	unsigned int tries;

	guard(mutex)(&dpin->lock);
	if (!dpin->leased)
		return IRQ_NONE;
	/* Match Apple's stable snapshot, but never spin indefinitely. */
	for (tries = 0; tries < 16; tries++) {
		pending = readl(dpin->regs + DPIN_IRQ_STATUS);
		hpd = readl(dpin->regs + DPIN_HPD);
		after = readl(dpin->regs + DPIN_IRQ_STATUS);
		if (pending == after)
			break;
	}
	if (tries == 16) {
		dpin_mask(dpin, DPIN_IRQ_ENABLE, DPIN_IRQ_MASK, 0);
		dev_err_ratelimited(dpin->dev,
				    "unstable DPIN interrupt status; interrupts masked\n");
		return IRQ_HANDLED;
	}
	pending &= DPIN_IRQ_MASK;
	if (!pending)
		return IRQ_NONE;
	writel(pending, dpin->regs + DPIN_IRQ_STATUS);
	if (pending & DPIN_IRQ_HPD_CHANGE)
		writel(hpd, dpin->regs + DPIN_HPD);
	WRITE_ONCE(dpin->hpd, !!(hpd & DPIN_HPD_LEVEL));
	/* Callback only queues work: it must not enter the DCP fabric lock. */
	dpin->notify(dpin->cookie, pending & DPIN_IRQ_HPD_PULSE);
	return IRQ_HANDLED;
}

bool apple_dpin_hpd(struct apple_dpin *dpin)
{
	return READ_ONCE(dpin->hpd);
}

int apple_dpin_begin(struct apple_dpin *dpin, void (*notify)(void *, bool), void *cookie)
{
	int ret;

	guard(mutex)(&dpin->lock);
	if (dpin->leased)
		return -EBUSY;
	ret = pm_runtime_resume_and_get(dpin->dev);
	if (ret < 0)
		return ret;
	dpin->notify = notify;
	dpin->cookie = cookie;
	dpin->leased = true;
	WRITE_ONCE(dpin->hpd, !!(readl(dpin->regs + DPIN_HPD) & DPIN_HPD_LEVEL));
	enable_irq(dpin->irq);
	dpin_mask(dpin, DPIN_IRQ_ENABLE, DPIN_IRQ_MASK, DPIN_IRQ_MASK);
	return 0;
}

/* Called without the DCP fabric lock by the firmware callback worker. */
static int __apple_dpin_set_active(struct apple_dpin *dpin, bool active)
{
	unsigned long deadline = jiffies + msecs_to_jiffies(1000);
	u32 wanted = active ? 0 : DPIN_INACTIVE;
	int ret = 0;

	lockdep_assert_held(&dpin->lock);
	if (!dpin->leased)
		return -ENOLINK;
	if (active && !(readl(dpin->regs + DPIN_HPD) & DPIN_HPD_LEVEL))
		return -ENOLINK;
	dpin_mask(dpin, DPIN_CONTROL, DPIN_INACTIVE, wanted);
	while ((readl(dpin->regs + DPIN_STATUS) & DPIN_INACTIVE) != wanted) {
		if (active && !(readl(dpin->regs + DPIN_HPD) & DPIN_HPD_LEVEL)) {
			ret = -ENOLINK;
			break;
		}
		if (time_after_eq(jiffies, deadline)) {
			ret = -ETIMEDOUT;
			break;
		}
		usleep_range(1000, 2000);
	}
	dev_info(dpin->dev, "DPIN active=%d ack=%#x ret=%d\n", active,
		 readl(dpin->regs + DPIN_STATUS), ret);
	return ret;
}

int apple_dpin_set_active(struct apple_dpin *dpin, bool active)
{
	guard(mutex)(&dpin->lock);
	return __apple_dpin_set_active(dpin, active);
}

int apple_dpin_end(struct apple_dpin *dpin)
{
	int ret;

	mutex_lock(&dpin->lock);
	if (!dpin->leased) {
		mutex_unlock(&dpin->lock);
		return 0;
	}
	ret = __apple_dpin_set_active(dpin, false);
	if (ret) {
		mutex_unlock(&dpin->lock);
		return ret; /* Keep power and ownership on uncertain deactivation. */
	}
	dpin_mask(dpin, DPIN_IRQ_ENABLE, DPIN_IRQ_MASK, 0);
	mutex_unlock(&dpin->lock);
	disable_irq(dpin->irq); /* Join the callback before dropping its cookie. */
	mutex_lock(&dpin->lock);
	dpin->leased = false;
	dpin->notify = NULL;
	dpin->cookie = NULL;
	WRITE_ONCE(dpin->hpd, false);
	mutex_unlock(&dpin->lock);
	pm_runtime_put_sync(dpin->dev);
	return 0;
}

static void apple_dpin_put(void *data)
{
	put_device(data);
}

struct apple_dpin *devm_apple_dpin_get(struct device *dev,
				     struct device_node *node, unsigned int index)
{
	struct device_node *np __free(device_node) =
		of_parse_phandle(node, "apple,typec-dpin", index);
	struct platform_device *pdev;
	struct apple_dpin *dpin;
	int ret;

	if (!np)
		return NULL;
	pdev = of_find_device_by_node(np);
	if (!pdev)
		return ERR_PTR(-EPROBE_DEFER);
	dpin = platform_get_drvdata(pdev);
	if (!dpin || !device_link_add(dev, &pdev->dev,
				      DL_FLAG_AUTOREMOVE_CONSUMER)) {
		put_device(&pdev->dev);
		return ERR_PTR(dpin ? -ENOMEM : -EPROBE_DEFER);
	}
	ret = devm_add_action_or_reset(dev, apple_dpin_put, &pdev->dev);
	return ret ? ERR_PTR(ret) : dpin;
}

static int apple_dpin_probe(struct platform_device *pdev)
{
	struct apple_dpin *dpin;
	int ret;

	dpin = devm_kzalloc(&pdev->dev, sizeof(*dpin), GFP_KERNEL);
	if (!dpin)
		return -ENOMEM;
	dpin->dev = &pdev->dev;
	mutex_init(&dpin->lock);
	dpin->regs = devm_platform_ioremap_resource(pdev, 0);
	if (IS_ERR(dpin->regs))
		return PTR_ERR(dpin->regs);
	dpin->irq = platform_get_irq(pdev, 0);
	if (dpin->irq < 0)
		return dpin->irq;
	ret = devm_request_threaded_irq(&pdev->dev, dpin->irq, NULL, apple_dpin_irq,
				       IRQF_ONESHOT | IRQF_NO_AUTOEN,
				       dev_name(&pdev->dev), dpin);
	if (ret)
		return ret;
	ret = devm_pm_runtime_enable(&pdev->dev);
	if (ret)
		return ret;
	platform_set_drvdata(pdev, dpin);
	return 0;
}

static const struct of_device_id apple_dpin_of_match[] = {
	{ .compatible = "apple,t6000-dpin" },
	{ }
};
MODULE_DEVICE_TABLE(of, apple_dpin_of_match);

static struct platform_driver apple_dpin_driver = {
	.probe = apple_dpin_probe,
	.driver = {
		.name = "apple-dpin",
		.of_match_table = apple_dpin_of_match,
		.suppress_bind_attrs = true,
	},
};

int apple_dpin_register(void)
{
	return platform_driver_register(&apple_dpin_driver);
}

void apple_dpin_unregister(void)
{
	platform_driver_unregister(&apple_dpin_driver);
}
