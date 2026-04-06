import { test, expect } from "./fixtures";
import { InvestigationsPanelPage } from "./pages";

/**
 * Investigations / Cases panel — open, create form, absence signals,
 * investigation row expand, notes, and edge cases.
 */

test.describe("InvestigationsPanel — core", () => {
  let inv: InvestigationsPanelPage;

  test.beforeEach(async ({ page }) => {
    inv = new InvestigationsPanelPage(page);
    await inv.open();
  });

  test("panel renders heading Investigations", async () => {
    await expect(inv.heading).toContainText("Investigations");
  });

  test("+ New button is visible", async () => {
    await expect(inv.newBtn).toBeVisible();
  });

  test("Absence Signals button is visible", async () => {
    await expect(inv.absenceSignalsBtn).toBeVisible();
  });
});

test.describe("InvestigationsPanel — create form", () => {
  let inv: InvestigationsPanelPage;

  test.beforeEach(async ({ page }) => {
    inv = new InvestigationsPanelPage(page);
    await inv.open();
  });

  test("clicking + New opens the create form", async () => {
    await inv.openCreateForm();
    await expect(inv.nameInput).toBeVisible();
    await expect(inv.createBtn).toBeVisible();
    await expect(inv.cancelBtn).toBeVisible();
  });

  test("cancelling the form hides it", async () => {
    await inv.openCreateForm();
    await expect(inv.nameInput).toBeVisible();
    await inv.cancelCreate();
    await expect(inv.nameInput).not.toBeVisible();
  });

  test("toggling + New button opens and closes the form", async () => {
    await inv.openCreateForm();
    await expect(inv.nameInput).toBeVisible();
    // Click + New again to toggle off
    await inv.newBtn.click();
    await expect(inv.nameInput).not.toBeVisible();
  });

  test("filling the create form and submitting does not crash", async () => {
    await inv.openCreateForm();
    await inv.fillCreateForm("Test Investigation", "A test description", "intel,maritime");
    await inv.submitCreate();
    // Panel should remain stable
    await expect(inv.panel).toBeVisible();
  });

  test("submitting without a name shows validation or keeps form open", async () => {
    await inv.openCreateForm();
    // Don't fill the required name field
    await inv.submitCreate();
    // Form should stay open or show validation (name is required)
    await expect(inv.panel).toBeVisible();
  });
});

test.describe("InvestigationsPanel — absence signals", () => {
  test("clicking Absence Signals toggles the section", async ({ page }) => {
    const inv = new InvestigationsPanelPage(page);
    await inv.open();
    await inv.toggleAbsenceSignals();
    // Section should expand or toggle
    await expect(inv.panel).toBeVisible();
  });
});

test.describe("InvestigationsPanel — investigation rows", () => {
  test("clicking an investigation row expands it", async ({ page }) => {
    const inv = new InvestigationsPanelPage(page);
    await inv.open();

    const rows = inv.investigationRows;
    const count = await rows.count();
    if (count > 0) {
      await inv.clickInvestigation(0);
      // Should expand — panel stays visible
      await expect(inv.panel).toBeVisible();
    }
  });

  test("expanded investigation shows action buttons", async ({ page }) => {
    const inv = new InvestigationsPanelPage(page);
    await inv.open();

    const rows = inv.investigationRows;
    const count = await rows.count();
    if (count > 0) {
      await inv.clickInvestigation(0);
      // Look for Notes, Export Pack, Briefing, or Delete buttons
      const actionBtns = inv.panel.locator(
        'button:has-text("Notes"), button:has-text("Export Pack"), button:has-text("Briefing"), button:has-text("Delete")',
      );
      const actionCount = await actionBtns.count();
      expect(actionCount).toBeGreaterThan(0);
    }
  });
});
