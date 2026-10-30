import { expect, test, type Page, type Request } from "@playwright/test";

const apiPrefix = "/mock-api/v1";
const accessToken = "e2e-access-token";
const user = {
  id: "user-1",
  email: "tester@example.test",
  full_name: "Test User",
  roles: ["institution_applicant"],
  is_active: true,
  institution_id: "institution-1",
  created_at: "2026-01-01T00:00:00Z"
};
const institution = {
  id: "institution-1",
  code: "TESTBANK",
  name: "Test Bank",
  approval_reference: null,
  contact_email: "ops@example.test",
  created_at: "2026-01-01T00:00:00Z"
};
const demoInstrument = {
  id: "instrument-1",
  institution_id: "institution-1",
  instrument_number: "SYN-FDR-E2E-001",
  bank_name: "Synthetic Test Bank",
  branch_name: "Demo branch",
  holder_name: "Synthetic Test Office",
  amount: "100000.00",
  issue_date: "2026-01-01",
  maturity_date: "2027-01-01",
  lifecycle_state: "active",
  created_at: "2026-01-01T00:00:00Z"
};
const demoRelease = {
  id: "release-1",
  instrument_id: demoInstrument.id,
  requested_by: "applicant-1",
  reviewed_by: "finance-1",
  status: "under_review",
  justification: "Synthetic final-approval workflow example.",
  review_note: "Finance review completed with synthetic evidence.",
  created_at: "2026-01-01T00:00:00Z"
};
const demoDocument = {
  id: "document-1",
  instrument_id: demoInstrument.id,
  original_filename: "SYNTHETIC-DEMO-NOT-A-BANK-FDR.pdf",
  mime_type: "application/pdf",
  size_bytes: 4096,
  sha256: "synthetic-hash",
  status: "uploaded",
  uploaded_by: "applicant-1",
  created_at: "2026-01-01T00:00:00Z"
};

type MockOptions = {
  loginStatus?: number;
  role?: string;
};

async function mockApi(page: Page, options: MockOptions = {}) {
  const requests: Request[] = [];
  let instrument: Record<string, unknown> | null = null;

  await page.route(`**${apiPrefix}/**`, async (route) => {
    const request = route.request();
    requests.push(request);
    const url = new URL(request.url());
    const path = url.pathname.slice(apiPrefix.length);
    const method = request.method();

    if (method === "POST" && path === "/auth/login") {
      if (options.loginStatus) {
        await route.fulfill({
          status: options.loginStatus,
          contentType: "application/json",
          body: JSON.stringify({ detail: "Incorrect email or password." })
        });
        return;
      }
      const signedInUser = {
        ...user,
        roles: [options.role ?? "institution_applicant"],
        institution_id: options.role && options.role !== "institution_applicant" ? null : user.institution_id
      };
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ access_token: accessToken, token_type: "bearer", user: signedInUser })
      });
      return;
    }

    if (method === "POST" && path === "/auth/register") {
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          access_token: accessToken,
          token_type: "bearer",
          user: { ...user, institution_id: null }
        })
      });
      return;
    }

    if (method === "GET" && path === "/users/me") {
      const currentUser = {
        ...user,
        roles: [options.role ?? "institution_applicant"],
        institution_id: options.role && options.role !== "institution_applicant" ? null : user.institution_id
      };
      await route.fulfill({ contentType: "application/json", body: JSON.stringify(currentUser) });
      return;
    }

    if (method === "GET" && path === "/dashboard/summary") {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          total_instruments: instrument ? 1 : 0,
          active_instruments: instrument ? 1 : 0,
          approaching_maturity: 0,
          total_value: instrument ? "12500.00" : "0",
          open_cases: 0
        })
      });
      return;
    }

    if (method === "GET" && path === "/instruments") {
      const currentInstrument =
        instrument ??
        (options.role && options.role !== "institution_applicant" ? demoInstrument : null);
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          items: currentInstrument ? [currentInstrument] : [],
          total: currentInstrument ? 1 : 0
        })
      });
      return;
    }

    if (method === "GET" && path === "/cases") {
      await route.fulfill({ contentType: "application/json", body: "[]" });
      return;
    }

    if (method === "GET" && path === "/releases/release-1") {
      await route.fulfill({ contentType: "application/json", body: JSON.stringify(demoRelease) });
      return;
    }

    if (method === "GET" && ["/releases", "/renewals", "/policy-rules", "/notifications"].includes(path)) {
      const releaseItems =
        path === "/releases" && ["finance_officer", "approving_authority"].includes(options.role ?? "")
          ? [{ ...demoRelease, status: options.role === "finance_officer" ? "submitted" : "under_review" }]
          : [];
      await route.fulfill({ contentType: "application/json", body: JSON.stringify(releaseItems) });
      return;
    }

    if (method === "GET" && path === "/institutions/me") {
      await route.fulfill({ contentType: "application/json", body: JSON.stringify(institution) });
      return;
    }

    if (method === "POST" && path === "/instruments") {
      const body = request.postDataJSON() as Record<string, string>;
      instrument = {
        id: "instrument-1",
        institution_id: institution.id,
        ...body,
        lifecycle_state: "active",
        created_at: "2026-01-01T00:00:00Z"
      };
      await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify(instrument) });
      return;
    }

    if (method === "GET" && path === "/instruments/instrument-1") {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(instrument ?? demoInstrument)
      });
      return;
    }

    if (method === "GET" && path === "/instruments/instrument-1/documents") {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(
          options.role === "approving_authority" ? [demoDocument] : []
        )
      });
      return;
    }

    await route.fulfill({
      status: 501,
      contentType: "application/json",
      body: JSON.stringify({ detail: `Unexpected test API request: ${method} ${path}` })
    });
  });

  return requests;
}

test("shows role-specific finance dashboard and hides scrutiny access", async ({ page }) => {
  await mockApi(page, { role: "finance_officer" });
  await page.goto("/");

  await page.getByLabel("Email").fill("finance@example.test");
  await page.getByLabel("Password").fill("correct-password");
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page.getByRole("heading", { name: "Finance dashboard" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Finance review", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Scrutiny queue" })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "FDR portfolio" })).toBeVisible();
});

for (const roleCase of [
  {
    role: "scrutiny_officer",
    heading: "Scrutiny dashboard",
    allowedLink: "Scrutiny",
    hiddenLink: "Finance review"
  },
  {
    role: "compliance_administrator",
    heading: "Compliance dashboard",
    allowedLink: "Escalations",
    hiddenLink: "Final approvals"
  },
  {
    role: "approving_authority",
    heading: "Approving authority dashboard",
    allowedLink: "Final approvals",
    hiddenLink: "Scrutiny queue"
  }
]) {
  test(`shows the ${roleCase.role} dashboard and role-specific navigation`, async ({ page }) => {
    await mockApi(page, { role: roleCase.role });
    await page.goto("/");

    await page.getByLabel("Email").fill(`${roleCase.role}@example.test`);
    await page.getByLabel("Password").fill("correct-password");
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page.getByRole("heading", { name: roleCase.heading })).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Workspace navigation" })).toBeVisible();
    await expect(page.locator(".sidebar-nav")).toHaveCSS("display", "grid");
    await expect(page.locator(".workflow-nav")).toHaveCount(0);
    await expect(page.getByRole("link", { name: roleCase.allowedLink, exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: roleCase.hiddenLink, exact: true })).toHaveCount(0);
    if (roleCase.role === "compliance_administrator") {
      await expect(page.getByRole("heading", { name: "Compliance rule versions" })).toBeVisible();
      await expect(page.getByRole("button", { name: "Publish rule version" })).toBeVisible();
    }
  });
}

test("blocks applicants from directly opening restricted audit workflows", async ({ page }) => {
  await mockApi(page);
  await page.addInitScript((token) => sessionStorage.setItem("deposit360_token", token), accessToken);
  await page.goto("/audit");

  await expect(page.locator(".notice-error")).toContainText(
    "This workflow is not available to your role."
  );
});

test("fills the selected demo role credentials from quick login", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: "Helpdesk Copilot" }).click();
  await expect(page.getByRole("dialog", { name: "Deposit360 Helpdesk Copilot" })).toBeVisible();
  await expect(page.locator(".helpdesk-bot-icon")).toBeVisible();
  await expect(page.getByRole("button", { name: "Helpdesk Copilot", exact: true })).not.toContainText("?");
  await expect(page.getByRole("button", { name: "How do I log in?" })).toBeVisible();
  await page.getByRole("button", { name: "How do I log in?" }).click();
  await expect(page.getByText(/choose a role under Quick demo login/i)).toBeVisible();
  await page.getByRole("button", { name: "Close Helpdesk Copilot" }).click();

  await page.getByRole("button", { name: "Finance Officer" }).click();

  await expect(page.getByLabel("Email")).toHaveValue("finance.deposit360@example.com");
  await expect(page.getByLabel("Password")).toHaveValue("Demo360-SIH-2026!");
});

test("provides role-aware help for release requests without exposing other-role tasks", async ({ page }) => {
  await mockApi(page, { role: "finance_officer" });
  await page.addInitScript((token) => sessionStorage.setItem("deposit360_token", token), accessToken);
  await page.goto("/");

  await page.getByRole("button", { name: "Helpdesk Copilot" }).click();
  await expect(page.getByRole("dialog", { name: "Deposit360 Helpdesk Copilot" })).toBeVisible();
  await expect(page.getByRole("button", { name: "What can Finance do with a release request?" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Record a final release decision" })).toHaveCount(0);

  await page.getByRole("button", { name: "What can Finance do with a release request?" }).click();
  await expect(page.getByText(/Finance reviews the deposit and supporting financial evidence/)).toBeVisible();
  await expect(
    page.getByRole("dialog", { name: "Deposit360 Helpdesk Copilot" })
      .getByRole("link", { name: "Open finance review" })
  ).toBeVisible();
});

test("suggests example questions after an unmatched helpdesk query", async ({ page }) => {
  await mockApi(page, { role: "scrutiny_officer" });
  await page.addInitScript((token) => sessionStorage.setItem("deposit360_token", token), accessToken);
  await page.goto("/");

  await page.getByRole("button", { name: "Helpdesk Copilot" }).click();
  await page.getByLabel("Ask for help").fill("Can you help me with something unusual?");
  await page.getByRole("button", { name: "Send question" }).click();

  await expect(page.getByText(/example questions you can ask as a Scrutiny Officer/i)).toBeVisible();
  await expect(page.getByRole("button", { name: "What should I check in a case?" })).toBeVisible();
  await expect(page.getByRole("button", { name: "How do I publish a compliance rule?" })).toHaveCount(0);

  await page.getByRole("button", { name: "What should I check in a case?" }).click();
  await expect(page.getByText(/Compare the submitted details with the available evidence/)).toBeVisible();
});

test("shows evidence and final-decision controls to the approving authority", async ({ page }) => {
  await mockApi(page, { role: "approving_authority" });
  await page.addInitScript((token) => sessionStorage.setItem("deposit360_token", token), accessToken);
  await page.goto("/releases/release-1");

  await expect(page.getByRole("heading", { name: "Release request" })).toBeVisible();
  await expect(page.getByText("SYNTHETIC-DEMO-NOT-A-BANK-FDR.pdf")).toBeVisible();
  await expect(page.getByLabel("Release decision")).toBeVisible();
  await expect(page.getByRole("button", { name: "Record final decision" })).toBeVisible();
});

test("shows a clear error for rejected sign-in without saving a session", async ({ page }) => {
  const requests = await mockApi(page, { loginStatus: 401 });
  await page.goto("/");

  await page.getByLabel("Email").fill("tester@example.test");
  await page.getByLabel("Password").fill("incorrect-password");
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page.locator(".error-message")).toHaveText("Incorrect email or password.");
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Sign in" })).toBeEnabled();
  expect(await page.evaluate(() => sessionStorage.getItem("deposit360_token"))).toBeNull();
  expect(requests.map((request) => new URL(request.url()).pathname)).toContain(
    `${apiPrefix}/auth/login`
  );
});

test("signs in, restores the dashboard session, and signs out", async ({ page }) => {
  await mockApi(page);
  await page.goto("/");

  await page.getByLabel("Email").fill("tester@example.test");
  await page.getByLabel("Password").fill("correct-password");
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page.getByRole("heading", { name: "Deposit dashboard" })).toBeVisible();
  await expect(page.getByText("No deposits yet. Create an institution, then add your first deposit."))
    .toBeVisible();
  expect(await page.evaluate(() => sessionStorage.getItem("deposit360_token"))).toBe(accessToken);

  await page.reload();
  await expect(page.getByRole("heading", { name: "Deposit dashboard" })).toBeVisible();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  expect(await page.evaluate(() => sessionStorage.getItem("deposit360_token"))).toBeNull();
});

test("registers an account and prompts the user to set up an institution", async ({ page }) => {
  const requests = await mockApi(page);
  await page.goto("/");

  await page.getByRole("button", { name: "Create an account" }).click();
  await expect(page.getByRole("heading", { name: "Create your account" })).toBeVisible();
  await expect(page.getByLabel("Password")).toHaveAttribute("minlength", "12");

  await page.getByLabel("Full name").fill("Test User");
  await page.getByLabel("Email").fill("tester@example.test");
  await page.getByLabel("Password").fill("a-strong-test-password");
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page.getByRole("heading", { name: "Deposit dashboard" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Set up your institution" })).toBeVisible();
  const registration = requests.find((request) => request.url().endsWith("/auth/register"));
  expect(registration?.postDataJSON()).toEqual({
    email: "tester@example.test",
    full_name: "Test User",
    password: "a-strong-test-password"
  });
});

test("registers a deposit and opens its lifecycle details", async ({ page }) => {
  const requests = await mockApi(page);
  await page.goto("/");

  await page.getByLabel("Email").fill("tester@example.test");
  await page.getByLabel("Password").fill("correct-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Deposit dashboard" })).toBeVisible();

  await page.getByRole("link", { name: "Register FDR" }).click();
  await expect(page.getByRole("heading", { name: "Register a deposit" })).toBeVisible();
  await page.getByLabel("Instrument number").fill("FD-E2E-001");
  await page.getByLabel("Bank", { exact: true }).fill("Test Bank");
  await page.getByLabel("Branch (optional)").fill("Central");
  await page.getByLabel("Account holder").fill("Test User");
  await page.getByLabel("Amount").fill("12500");
  await page.getByLabel("Issue date").fill("2026-01-01");
  await page.getByLabel("Maturity date").fill("2027-01-01");
  await page.getByRole("button", { name: "Register deposit" }).click();

  expect(requests.map((request) => `${request.method()} ${new URL(request.url()).pathname}`))
    .toContain(`POST ${apiPrefix}/instruments`);
  await expect(page).toHaveURL(/\/lifecycle\/instrument-1$/, { timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "FD-E2E-001" })).toBeVisible();
  await expect(page.getByText("Test Bank · Test User")).toBeVisible();
  await expect(page.getByText("No documents uploaded.")).toBeVisible();

  const creation = requests.find(
    (request) => request.method() === "POST" && request.url().endsWith("/instruments")
  );
  expect(creation?.postDataJSON()).toEqual({
    instrument_number: "FD-E2E-001",
    bank_name: "Test Bank",
    branch_name: "Central",
    holder_name: "Test User",
    amount: "12500",
    issue_date: "2026-01-01",
    maturity_date: "2027-01-01"
  });
});
