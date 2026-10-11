// SPDX-License-Identifier: GPL-2.0-only OR MIT
/*
 * KUnit test of the display gate, run on test device trees instead of a
 * Mac's: the gate's own init code decides, applies its changes and adds the
 * PMP from its built-in overlay.
 *  - T6031 (t6031-gate-test.dtso): off by default, enabled only by
 *    apple_t6031_display.enable=1 with the full handoff, and nothing changed
 *    when a check fails.
 *  - T6030 (t6030-gate-test.dtso): on by default, as before, and
 *    the T6031 switch does not change it.
 * Included at the end of t6030-display-gate.c.
 *
 * The test trees are applied once and stay: the gate gives some properties
 * names it does not allocate, which the tree must never free. Each case
 * reverts the gate's changes and its own.
 */

#include <kunit/test.h>

extern const u8 __dtbo_t6031_gate_test_begin[];
extern const u8 __dtbo_t6031_gate_test_end[];
extern const u8 __dtbo_t6030_gate_test_begin[];
extern const u8 __dtbo_t6030_gate_test_end[];

/* One SoC's test tree and what the gate should make of it. */
struct gt_soc {
	const struct gate_soc *soc;
	const u8 *fixture, *fixture_end;
	const char *nodes[GATE_NR_NODES];	/* what the gate enables */
	const char *dcp, *display, *values, *aic;
	const char *ps[PMP_PS_NR];		/* as PMP_PS_* */
	const char *report_compat, *disp_entry, *pmp_compat, *pmp_dart, *pmp_mbox;
};

static const struct gt_soc gt_t6031 __initconst = {
	.soc = &gate_t6031,
	.fixture = __dtbo_t6031_gate_test_begin,
	.fixture_end = __dtbo_t6031_gate_test_end,
	.nodes = { "/soc/dcp@386c00000", "/soc/display-subsystem", "/soc/mailbox@386c08000",
		   "/soc/iommu@38530c000", "/soc/iommu@385304000" },
	.dcp = "/soc/dcp@386c00000",
	.display = "/soc/display-subsystem",
	.values = "/chosen/asahi,t6031-pmp",
	.aic = "/soc/interrupt-controller@292400000",
	.ps = {
		[PMP_PS_DISP_SYS] = "/soc/power-management@292280000/power-controller@200",
		[PMP_PS_DISP_FE] = "/soc/power-management@292280000/power-controller@298",
		[PMP_PS_DISP_CPU] = "/soc/power-management@292280000/power-controller@2a0",
		[PMP_PS_PMP] = "/soc/power-management@292800000/power-controller@550",
		[PMP_PS_PMS_SRAM] = "/soc/power-management@292800000/power-controller@560",
	},
	.report_compat = "apple,t6031-pmp-v2-report",
	.disp_entry = "report@10",
	.pmp_compat = "apple,t6031-pmp-v2",
	.pmp_dart = "iommu@290300000",
	.pmp_mbox = "mailbox@290c08000",
};

static const struct gt_soc gt_t6030 __initconst = {
	.soc = &gate_t6030,
	.fixture = __dtbo_t6030_gate_test_begin,
	.fixture_end = __dtbo_t6030_gate_test_end,
	.nodes = { "/soc/dcp@28ec00000", "/soc/display-subsystem-t6030", "/soc/mailbox@28ec08000",
		   "/soc/iommu@28d30c000", "/soc/iommu@28d304000" },
	.dcp = "/soc/dcp@28ec00000",
	.display = "/soc/display-subsystem-t6030",
	.values = "/chosen/asahi,t6030-pmp",
	.aic = "/soc/interrupt-controller@351000000",
	.ps = {
		[PMP_PS_DISP_SYS] = "/soc/power-management@350700000/power-controller@1c0",
		[PMP_PS_DISP_FE] = "/soc/power-management@350700000/power-controller@258",
		[PMP_PS_DISP_CPU] = "/soc/power-management@350700000/power-controller@10000",
		[PMP_PS_PMP] = "/soc/power-management@350700000/power-controller@4c8",
		[PMP_PS_PMS_SRAM] = "/soc/power-management@350700000/power-controller@4d0",
	},
	.report_compat = "apple,t6030-pmp-v2-report",
	.disp_entry = "report@7",
	.pmp_compat = "apple,t6030-pmp-v2",
	.pmp_dart = "iommu@350300000",
	.pmp_mbox = "mailbox@350c08000",
};

static int gt_fixture_t6031 __initdata = -1;
static int gt_fixture_t6030 __initdata = -1;

struct gate_test {
	const struct gt_soc *s;
	struct of_changeset cs;	/* this case's own edits to the test tree */
	bool requested, t6031_requested;
};

static struct device_node *__init gt_node(struct kunit *test, const char *path)
{
	struct device_node *np = of_find_node_by_path(path);

	KUNIT_ASSERT_NOT_NULL_MSG(test, np, "no %s", path);
	/* The test trees are never removed: a reference is not needed. */
	of_node_put(np);
	return np;
}

/* Edits of the test tree, applied by gt_run() before the gate runs. */
static void __init gt_remove(struct kunit *test, const char *path, const char *name)
{
	struct gate_test *t = test->priv;
	struct device_node *np = gt_node(test, path);
	struct property *prop = of_find_property(np, name, NULL);

	KUNIT_ASSERT_NOT_NULL(test, prop);
	KUNIT_ASSERT_EQ(test, of_changeset_remove_property(&t->cs, np, prop), 0);
}

static void __init gt_add_u32(struct kunit *test, const char *path, const char *name, u32 val)
{
	struct gate_test *t = test->priv;

	KUNIT_ASSERT_EQ(test, of_changeset_add_prop_u32(&t->cs, gt_node(test, path), name, val), 0);
}

static void __init gt_set_u32(struct kunit *test, const char *path, const char *name, u32 val)
{
	gt_remove(test, path, name);
	gt_add_u32(test, path, name, val);
}

static void __init gt_set_string(struct kunit *test, const char *path, const char *name,
				 const char *val)
{
	struct gate_test *t = test->priv;

	KUNIT_ASSERT_EQ(test, of_changeset_update_prop_string(&t->cs, gt_node(test, path),
							      name, val), 0);
}

static void __init gt_detach(struct kunit *test, const char *path)
{
	struct gate_test *t = test->priv;

	KUNIT_ASSERT_EQ(test, of_changeset_detach_node(&t->cs, gt_node(test, path)), 0);
}

static void __init gt_run(struct kunit *test)
{
	struct gate_test *t = test->priv;

	KUNIT_ASSERT_EQ(test, of_changeset_apply(&t->cs), 0);
	gate_run();
}

static bool __init gt_okay(struct kunit *test, const char *path)
{
	return of_device_is_available(gt_node(test, path));
}

static u32 __init gt_u32(struct kunit *test, const char *path, const char *name)
{
	u32 val = 0;

	KUNIT_EXPECT_EQ_MSG(test, of_property_read_u32(gt_node(test, path), name, &val), 0,
			    "%s %s", path, name);
	return val;
}

/* Nothing enabled, no PMP added, no property of the gate's left behind. */
static void __init gt_expect_untouched(struct kunit *test)
{
	struct gate_test *t = test->priv;
	const struct gt_soc *s = t->s;
	struct device_node *report;
	int i;

	for (i = 0; i < GATE_NR_NODES; i++)
		KUNIT_EXPECT_FALSE_MSG(test, gt_okay(test, s->nodes[i]), "%s enabled", s->nodes[i]);
	report = of_find_compatible_node(NULL, NULL, s->report_compat);
	KUNIT_EXPECT_NULL(test, report);
	of_node_put(report);
	KUNIT_EXPECT_FALSE(test, of_property_present(gt_node(test, s->dcp), "apple,pmp-report"));
	KUNIT_EXPECT_FALSE(test, of_property_present(gt_node(test, s->ps[PMP_PS_DISP_SYS]),
						     "apple,min-state"));
	KUNIT_EXPECT_FALSE(test, of_property_present(gt_node(test, s->ps[PMP_PS_PMP]),
						     "apple,always-on"));
	KUNIT_EXPECT_EQ(test, gate_pmp_ovcs, 0);
}

/* The display enabled, with the PMP of this SoC behind it. */
static void __init gt_expect_enabled(struct kunit *test)
{
	struct gate_test *t = test->priv;
	const struct gt_soc *s = t->s;
	struct device_node *entry, *report, *pmp, *dart, *mbox, *aic;
	const char *uuid = NULL;
	u32 parent = 0;
	int i;

	for (i = 0; i < GATE_NR_NODES; i++)
		KUNIT_EXPECT_TRUE_MSG(test, gt_okay(test, s->nodes[i]), "%s not enabled",
				      s->nodes[i]);
	KUNIT_EXPECT_NE(test, gate_pmp_ovcs, 0);

	/* The DCP waits for the internal display request. */
	entry = of_parse_phandle(gt_node(test, s->dcp), "apple,pmp-report", 0);
	KUNIT_ASSERT_NOT_NULL(test, entry);
	KUNIT_EXPECT_STREQ(test, of_node_full_name(entry), s->disp_entry);
	KUNIT_EXPECT_TRUE(test, of_device_is_available(entry));
	report = of_get_parent(entry);
	of_node_put(entry);
	KUNIT_EXPECT_TRUE(test, of_device_is_compatible(report, s->report_compat));

	/* The PMP holds this Mac's values and stays halted for the report driver. */
	pmp = of_parse_phandle(report, "apple,pmp", 0);
	of_node_put(report);
	KUNIT_ASSERT_NOT_NULL(test, pmp);
	KUNIT_EXPECT_TRUE(test, of_device_is_compatible(pmp, s->pmp_compat));
	KUNIT_EXPECT_FALSE(test, of_device_is_available(pmp));
	KUNIT_ASSERT_EQ(test, of_property_read_string(pmp, "apple,tunable-uuid", &uuid), 0);
	KUNIT_EXPECT_STREQ(test, uuid, "2F4EB4C4-001B-3ACF-A9A0-68D8E42FC3A7");
	KUNIT_EXPECT_TRUE(test, of_property_present(pmp, "apple,tunable-test"));
	KUNIT_EXPECT_TRUE(test, of_property_present(pmp, "apple,board-id"));
	KUNIT_EXPECT_TRUE(test, of_property_present(pmp, "apple,dram-vendor-id"));

	/* Its DART and mailbox interrupt through the DCP mailbox's parent. */
	aic = gt_node(test, s->aic);
	dart = of_parse_phandle(pmp, "iommus", 0);
	mbox = of_parse_phandle(pmp, "mboxes", 0);
	of_node_put(pmp);
	KUNIT_ASSERT_NOT_NULL(test, dart);
	KUNIT_ASSERT_NOT_NULL(test, mbox);
	KUNIT_EXPECT_STREQ(test, of_node_full_name(dart), s->pmp_dart);
	KUNIT_EXPECT_STREQ(test, of_node_full_name(mbox), s->pmp_mbox);
	KUNIT_EXPECT_FALSE(test, of_device_is_available(dart));
	KUNIT_EXPECT_FALSE(test, of_device_is_available(mbox));
	KUNIT_EXPECT_EQ(test, of_property_read_u32(dart, "interrupt-parent", &parent), 0);
	KUNIT_EXPECT_EQ(test, parent, aic->phandle);
	parent = 0;
	KUNIT_EXPECT_EQ(test, of_property_read_u32(mbox, "interrupt-parent", &parent), 0);
	KUNIT_EXPECT_EQ(test, parent, aic->phandle);
	of_node_put(mbox);
	of_node_put(dart);

	/* The display floors, and the PMP domains kept on. */
	for (i = PMP_PS_DISP_SYS; i <= PMP_PS_DISP_CPU; i++)
		KUNIT_EXPECT_EQ(test, gt_u32(test, s->ps[i], "apple,min-state"), PMGR_PS_ACTIVE);
	for (i = PMP_PS_PMP; i <= PMP_PS_PMS_SRAM; i++)
		KUNIT_EXPECT_TRUE(test, of_property_read_bool(gt_node(test, s->ps[i]),
							      "apple,always-on"));
}

static int __init gt_apply_fixture(const struct gt_soc *s, int *id)
{
	return of_overlay_fdt_apply(s->fixture, s->fixture_end - s->fixture, id, NULL);
}

static int __init gt_suite_init_t6031(struct kunit_suite *suite)
{
	return gt_apply_fixture(&gt_t6031, &gt_fixture_t6031);
}

static int __init gt_suite_init_t6030(struct kunit_suite *suite)
{
	return gt_apply_fixture(&gt_t6030, &gt_fixture_t6030);
}

static int __init gt_init(struct kunit *test, const struct gt_soc *s)
{
	struct gate_test *t = kunit_kzalloc(test, sizeof(*t), GFP_KERNEL);

	if (!t)
		return -ENOMEM;
	test->priv = t;
	t->s = s;
	/* As the boot left them: the test kernel's command line sets neither. */
	t->requested = gate_requested;
	t->t6031_requested = gate_t6031_requested;
	of_changeset_init(&t->cs);
	gate_soc = s->soc;
	gate_pmp_values = NULL;
	gate_pmp_ovcs = 0;
	gate_requested = true;
	gate_t6031_requested = false;
	return 0;
}

static int __init gt_init_t6031(struct kunit *test)
{
	return gt_init(test, &gt_t6031);
}

static int __init gt_init_t6030(struct kunit *test)
{
	return gt_init(test, &gt_t6030);
}

static void __init gt_exit(struct kunit *test)
{
	struct gate_test *t = test->priv;

	/* The gate leaves its changes applied only when it enabled the display. */
	if (gate_pmp_ovcs) {
		of_changeset_revert(&gate_pmp_cs);
		of_changeset_destroy(&gate_pmp_cs);
		of_overlay_remove(&gate_pmp_ovcs);
		gate_pmp_ovcs = 0;
		of_changeset_revert(&gate_cs);
		of_changeset_destroy(&gate_cs);
	}
	of_changeset_revert(&t->cs);
	of_changeset_destroy(&t->cs);
	of_node_put(gate_pmp_values);
	gate_pmp_values = NULL;
	gate_requested = t->requested;
	gate_t6031_requested = t->t6031_requested;
	gate_soc = NULL;
}

/* T6031 */

/* The boot defaults, and the T6031 switch apart from the others. */
static void __init gate_t6031_param(struct kunit *test)
{
	struct gate_test *t = test->priv;

	KUNIT_EXPECT_FALSE(test, t->t6031_requested);
	KUNIT_EXPECT_TRUE(test, t->requested);

	KUNIT_EXPECT_EQ(test, gate_setup_t6031("1"), 0);
	KUNIT_EXPECT_TRUE(test, gate_t6031_requested);
	KUNIT_EXPECT_EQ(test, gate_setup_t6031("0"), 0);
	KUNIT_EXPECT_FALSE(test, gate_t6031_requested);
	KUNIT_EXPECT_NE(test, gate_setup_t6031("maybe"), 0);
	KUNIT_EXPECT_FALSE(test, gate_t6031_requested);
	KUNIT_EXPECT_NE(test, gate_setup_t6031(NULL), 0);
	KUNIT_EXPECT_FALSE(test, gate_t6031_requested);

	/* The T6030 and T8122 escapes do not touch it, nor it them. */
	KUNIT_EXPECT_EQ(test, gate_setup("0"), 0);
	KUNIT_EXPECT_FALSE(test, gate_requested);
	KUNIT_EXPECT_FALSE(test, gate_t6031_requested);
	KUNIT_EXPECT_EQ(test, gate_setup_t6031("1"), 0);
	KUNIT_EXPECT_FALSE(test, gate_requested);
	KUNIT_EXPECT_EQ(test, gate_setup_t8122("1"), 0);
	KUNIT_EXPECT_TRUE(test, gate_requested);
	KUNIT_EXPECT_TRUE(test, gate_t6031_requested);
}

/* With a complete handoff and no command line switch, nothing changes. */
static void __init gate_t6031_off_by_default(struct kunit *test)
{
	gt_run(test);
	gt_expect_untouched(test);
}

static void __init gate_t6031_switched_off(struct kunit *test)
{
	KUNIT_ASSERT_EQ(test, gate_setup_t6031("1"), 0);
	KUNIT_ASSERT_EQ(test, gate_setup_t6031("0"), 0);
	gt_run(test);
	gt_expect_untouched(test);
}

/* apple_t6031_display.enable=1 and the full handoff: the T6030 result. */
static void __init gate_t6031_enabled(struct kunit *test)
{
	/* apple_t6030_display.enable=0 is not the T6031 switch. */
	KUNIT_ASSERT_EQ(test, gate_setup("0"), 0);
	KUNIT_ASSERT_EQ(test, gate_setup_t6031("1"), 0);
	gt_run(test);
	gt_expect_enabled(test);
}

static void __init gate_t6031_no_dcp_marker(struct kunit *test)
{
	KUNIT_ASSERT_EQ(test, gate_setup_t6031("1"), 0);
	gt_remove(test, gt_t6031.dcp, "apple,t6031-handoff");
	gt_run(test);
	gt_expect_untouched(test);
}

static void __init gate_t6031_no_display_marker(struct kunit *test)
{
	KUNIT_ASSERT_EQ(test, gate_setup_t6031("1"), 0);
	gt_remove(test, gt_t6031.display, "apple,t6031-handoff");
	gt_run(test);
	gt_expect_untouched(test);
}

static void __init gate_t6031_marker_not_one(struct kunit *test)
{
	KUNIT_ASSERT_EQ(test, gate_setup_t6031("1"), 0);
	gt_set_u32(test, gt_t6031.dcp, "apple,t6031-handoff", 2);
	gt_run(test);
	gt_expect_untouched(test);
}

/* The T6030 marker is not the T6031 one. */
static void __init gate_t6031_t6030_marker(struct kunit *test)
{
	KUNIT_ASSERT_EQ(test, gate_setup_t6031("1"), 0);
	gt_remove(test, gt_t6031.dcp, "apple,t6031-handoff");
	gt_remove(test, gt_t6031.display, "apple,t6031-handoff");
	gt_add_u32(test, gt_t6031.dcp, "apple,t6030-handoff", 1);
	gt_add_u32(test, gt_t6031.display, "apple,t6030-handoff", 1);
	gt_run(test);
	gt_expect_untouched(test);
}

/* No fallback values on T6031. */
static void __init gate_t6031_no_pmp_values(struct kunit *test)
{
	KUNIT_ASSERT_EQ(test, gate_setup_t6031("1"), 0);
	gt_detach(test, gt_t6031.values);
	gt_run(test);
	gt_expect_untouched(test);
}

static void __init gate_t6031_incomplete_pmp_values(struct kunit *test)
{
	KUNIT_ASSERT_EQ(test, gate_setup_t6031("1"), 0);
	gt_remove(test, gt_t6031.values, "apple,board-id");
	gt_run(test);
	gt_expect_untouched(test);
}

static void __init gate_t6031_other_pmp_image(struct kunit *test)
{
	KUNIT_ASSERT_EQ(test, gate_setup_t6031("1"), 0);
	gt_set_string(test, gt_t6031.values, "apple,tunable-uuid",
		      "3B18C886-4C70-349B-B1C4-70F35DE2C5CD");
	gt_run(test);
	gt_expect_untouched(test);
}

/* The DCP on DISP_CPU, as on T6030, is not the T6031 power layout. */
static void __init gate_t6031_t6030_power_layout(struct kunit *test)
{
	KUNIT_ASSERT_EQ(test, gate_setup_t6031("1"), 0);
	gt_set_u32(test, gt_t6031.dcp, "power-domains",
		   gt_node(test, gt_t6031.ps[PMP_PS_DISP_CPU])->phandle);
	gt_run(test);
	gt_expect_untouched(test);
}

static void __init gate_t6031_not_inherited_on(struct kunit *test)
{
	KUNIT_ASSERT_EQ(test, gate_setup_t6031("1"), 0);
	gt_remove(test, gt_t6031.ps[PMP_PS_DISP_CPU], "apple,inherited-on");
	gt_run(test);
	gt_expect_untouched(test);
}

/* Last: the enabled path again, after every refusal was undone. */
static void __init gate_t6031_enabled_again(struct kunit *test)
{
	gate_t6031_enabled(test);
}

/* T6030: unchanged */

/* On by default: the T6031 switch, set or not, does not matter. */
static void __init gate_t6030_default_on(struct kunit *test)
{
	KUNIT_ASSERT_EQ(test, gate_setup_t6031("0"), 0);
	gt_run(test);
	gt_expect_enabled(test);
}

static void __init gate_t6030_escape(struct kunit *test)
{
	KUNIT_ASSERT_EQ(test, gate_setup_t6031("1"), 0);
	KUNIT_ASSERT_EQ(test, gate_setup("0"), 0);
	gt_run(test);
	gt_expect_untouched(test);
}

static void __init gate_t6030_t8122_escape(struct kunit *test)
{
	KUNIT_ASSERT_EQ(test, gate_setup_t8122("0"), 0);
	gt_run(test);
	gt_expect_untouched(test);
}

static void __init gate_t6030_no_marker(struct kunit *test)
{
	gt_remove(test, gt_t6030.dcp, "apple,t6030-handoff");
	gt_run(test);
	gt_expect_untouched(test);
}

/* The DCP on DISP_FE, as on T6031, is not the T6030 power layout. */
static void __init gate_t6030_t6031_power_layout(struct kunit *test)
{
	gt_set_u32(test, gt_t6030.dcp, "power-domains",
		   gt_node(test, gt_t6030.ps[PMP_PS_DISP_FE])->phandle);
	gt_run(test);
	gt_expect_untouched(test);
}

static void __init gate_t6030_other_pmp_image(struct kunit *test)
{
	gt_set_string(test, gt_t6030.values, "apple,tunable-uuid",
		      "3B18C886-4C70-349B-B1C4-70F35DE2C5CD");
	gt_run(test);
	gt_expect_untouched(test);
}

static void __init gate_t6030_enabled_again(struct kunit *test)
{
	gt_run(test);
	gt_expect_enabled(test);
}

/* The case and suite structs outlive init: only the functions are init code. */
static struct kunit_case gate_t6031_cases[] __refdata = {
	KUNIT_CASE(gate_t6031_param),
	KUNIT_CASE(gate_t6031_off_by_default),
	KUNIT_CASE(gate_t6031_switched_off),
	KUNIT_CASE(gate_t6031_enabled),
	KUNIT_CASE(gate_t6031_no_dcp_marker),
	KUNIT_CASE(gate_t6031_no_display_marker),
	KUNIT_CASE(gate_t6031_marker_not_one),
	KUNIT_CASE(gate_t6031_t6030_marker),
	KUNIT_CASE(gate_t6031_no_pmp_values),
	KUNIT_CASE(gate_t6031_incomplete_pmp_values),
	KUNIT_CASE(gate_t6031_other_pmp_image),
	KUNIT_CASE(gate_t6031_t6030_power_layout),
	KUNIT_CASE(gate_t6031_not_inherited_on),
	KUNIT_CASE(gate_t6031_enabled_again),
	{}
};

static struct kunit_suite gate_t6031_suite __refdata = {
	.name = "apple-display-gate-t6031",
	.suite_init = gt_suite_init_t6031,
	.init = gt_init_t6031,
	.exit = gt_exit,
	.test_cases = gate_t6031_cases,
};

static struct kunit_case gate_t6030_cases[] __refdata = {
	KUNIT_CASE(gate_t6030_default_on),
	KUNIT_CASE(gate_t6030_escape),
	KUNIT_CASE(gate_t6030_t8122_escape),
	KUNIT_CASE(gate_t6030_no_marker),
	KUNIT_CASE(gate_t6030_t6031_power_layout),
	KUNIT_CASE(gate_t6030_other_pmp_image),
	KUNIT_CASE(gate_t6030_enabled_again),
	{}
};

static struct kunit_suite gate_t6030_suite __refdata = {
	.name = "apple-display-gate-t6030",
	.suite_init = gt_suite_init_t6030,
	.init = gt_init_t6030,
	.exit = gt_exit,
	.test_cases = gate_t6030_cases,
};

kunit_test_init_section_suites(&gate_t6031_suite, &gate_t6030_suite);
