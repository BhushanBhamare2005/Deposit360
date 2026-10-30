"use client";

import { useRef, useState, type FormEvent } from "react";
import Link from "next/link";

type HelpTopic = {
  title: string;
  prompts: string[];
  keywords: string[];
  roles: string[];
  answer: string;
  steps: string[];
  href?: string;
  linkLabel?: string;
};

type HelpMessage = {
  id: number;
  sender: "user" | "copilot";
  text: string;
  topic?: HelpTopic;
  suggestedPrompts?: string[];
};

const allRoles = [
  "institution_applicant",
  "institution_user",
  "scrutiny_officer",
  "compliance_administrator",
  "finance_officer",
  "approving_authority",
  "auditor",
  "admin"
];

const topics: HelpTopic[] = [
  {
    title: "Sign in or choose a demo role",
    prompts: ["How do I log in?", "How do I use the demo accounts?"],
    keywords: [
      "login", "log in", "sign in", "password", "credential", "account",
      "role", "demo", "access", "forgot"
    ],
    roles: ["public"],
    answer: "No problem! On this sign-in page, choose a role under Quick demo login. That fills in the demo email and password for you; then press Sign in.",
    steps: [
      "Choose Institution Applicant, Scrutiny Officer, Compliance Administrator, Finance Officer, or Approving Authority.",
      "The demo email and shared local-demo password are filled into the form; you still click Sign in to continue.",
      "For a new account, choose Create an account. Public registration creates an Institution Applicant account. Password reset is not configured in this prototype."
    ]
  },
  {
    title: "Get started with an FDR",
    prompts: ["What can I do in Deposit360?", "What is an FDR?"],
    keywords: ["fdr", "fixed", "deposit", "start", "begin", "help", "guide", "what"],
    roles: ["public"],
    answer: "An FDR is a fixed deposit receipt. Deposit360 helps an institution submit deposit details and evidence, then follow review and release steps.",
    steps: [
      "Sign in as an Institution Applicant to register FDR details and supporting documents.",
      "Reviewers check submissions, and may request corrections.",
      "Finance and the Approving Authority handle release requests in separate stages."
    ]
  },
  {
    title: "Register an FDR",
    prompts: ["How do I add an FDR?", "Where do I submit a deposit?"],
    keywords: ["register", "submit", "upload", "add", "new", "fdr", "deposit"],
    roles: ["institution_applicant", "institution_user"],
    answer: "Enter the FDR details as they appear on your document, then attach the supporting evidence from its lifecycle page.",
    steps: [
      "Open Register FDR in the sidebar and enter the instrument number, bank, holder, amount, and dates.",
      "Save the deposit, then open its lifecycle details to upload supporting documents.",
      "Check My submissions for its current status and any review notes."
    ],
    href: "/institution/submit",
    linkLabel: "Open FDR registration"
  },
  {
    title: "Respond to a correction request",
    prompts: ["How do I fix a returned submission?", "Where can I see requested corrections?"],
    keywords: ["correction", "correct", "returned", "resubmit", "change", "fix", "request"],
    roles: ["institution_applicant", "institution_user"],
    answer: "A correction request includes a reviewer note. Update the supporting evidence and resubmit the case from your submissions.",
    steps: [
      "Open My submissions and locate the case marked Changes requested.",
      "Read the review note and upload corrected supporting evidence to the deposit.",
      "Use the case resubmission action so the reviewer can continue."
    ],
    href: "/institution/my-submissions",
    linkLabel: "Open my submissions"
  },
  {
    title: "Request a release",
    prompts: ["How do I request a deposit release?", "How does release approval work?"],
    keywords: ["release", "released", "approve", "approval", "request"],
    roles: ["institution_applicant", "institution_user"],
    answer: "Submit a release request with a clear reason. Finance and the Approving Authority then review it in separate stages.",
    steps: [
      "Open Releases and select the deposit.",
      "Enter the reason and submit the request.",
      "Track the status and reviewer notes on the release request."
    ],
    href: "/releases",
    linkLabel: "Open release requests"
  },
  {
    title: "Review a scrutiny case",
    prompts: ["What should I check in a case?", "How do I request corrections?"],
    keywords: ["scrutiny", "case", "review", "correction", "discrepancy", "evidence"],
    roles: ["scrutiny_officer", "admin"],
    answer: "Compare the submitted details with the available evidence, record a clear note, and choose a case outcome.",
    steps: [
      "Open Scrutiny and select a case.",
      "Review the FDR details and supporting documents; treat OCR output as an aid, not proof.",
      "Move the case to review, request corrections, approve, or reject with an explanatory note."
    ],
    href: "/scrutiny",
    linkLabel: "Open scrutiny"
  },
  {
    title: "Manage compliance and verification",
    prompts: ["How do I publish a compliance rule?", "Does verification prove the FDR is genuine?"],
    keywords: ["compliance", "rule", "policy", "verification", "verify", "bank", "authentic", "genuine"],
    roles: ["compliance_administrator", "admin"],
    answer: "Compliance rules are versioned for the demo. The configured verification adapter is simulated unless an authorized provider is connected.",
    steps: [
      "Review escalated cases and the evidence available to your role.",
      "Publish a new rule version with its effective date when policy changes.",
      "Never treat OCR, matching, or simulated verification as proof of bank authenticity."
    ],
    href: "/scrutiny",
    linkLabel: "Open compliance work"
  },
  {
    title: "Complete finance review",
    prompts: ["What can Finance do with a release request?", "How do I review a renewal?"],
    keywords: ["finance", "release", "review", "renewal", "maturity", "maturing"],
    roles: ["finance_officer", "admin"],
    answer: "Finance reviews the deposit and supporting financial evidence, then forwards eligible release requests for final approval.",
    steps: [
      "Check the deposit register, maturity details, and related evidence.",
      "Review submitted release requests and record a finance note.",
      "Move a request to Under review to send it to the Approving Authority; Finance does not make the final decision."
    ],
    href: "/releases",
    linkLabel: "Open finance review"
  },
  {
    title: "Record a final release decision",
    prompts: ["When can I approve a release?", "How do I make the final decision?"],
    keywords: ["approve", "approval", "final", "decision", "release", "reject"],
    roles: ["approving_authority", "admin"],
    answer: "The final decision is available after Finance has completed its review and moved the request to Under review.",
    steps: [
      "Open Final approvals and select a finance-cleared request.",
      "Review the request, finance note, deposit details, and attached evidence.",
      "Record approval or rejection with a clear decision note. Approval updates the deposit lifecycle."
    ],
    href: "/releases",
    linkLabel: "Open final approvals"
  },
  {
    title: "Review the audit trail",
    prompts: ["Where can I find the audit history?"],
    keywords: ["audit", "history", "log", "event"],
    roles: ["compliance_administrator", "approving_authority", "auditor", "admin"],
    answer: "The audit trail records workflow actions and administrative changes available to your role.",
    steps: ["Open Audit history from the sidebar.", "Select an event to inspect its details."],
    href: "/audit",
    linkLabel: "Open audit history"
  },
  {
    title: "Understand demo data and verification",
    prompts: ["Is this real bank data?", "Does OCR confirm the document is genuine?"],
    keywords: ["synthetic", "demo", "ocr", "authentic", "genuine", "real", "bank", "data"],
    roles: allRoles,
    answer: "The seeded FDR records and documents are fabricated for demonstration. OCR and match results do not confirm a bank deposit or document authenticity.",
    steps: [
      "Treat records prefixed SYN- as synthetic examples.",
      "Use OCR and matching only as review aids.",
      "Show a bank-confirmed result only if an authorized bank provider actually returned it."
    ]
  },
  {
    title: "Find notifications",
    prompts: ["Where are my notifications?"],
    keywords: ["notification", "alert", "message"],
    roles: allRoles,
    answer: "Notifications show workflow updates for your account. Available actions depend on each notification's status.",
    steps: ["Open Notifications in the sidebar.", "Read an update and acknowledge it when an acknowledgement action is available."],
    href: "/notifications",
    linkLabel: "Open notifications"
  }
];

function roleLabel(roles: string[]) {
  const role = roles[0] ?? "";
  const labels: Record<string, string> = {
    institution_applicant: "Institution Applicant",
    institution_user: "Institution Applicant",
    scrutiny_officer: "Scrutiny Officer",
    compliance_administrator: "Compliance Administrator",
    finance_officer: "Finance Officer",
    approving_authority: "Approving Authority",
    auditor: "Auditor",
    admin: "Administrator"
  };
  return labels[role] ?? "Deposit360 user";
}

function visibleTopics(roles: string[]) {
  const activeRoles = roles.length > 0 ? roles : ["public"];
  return topics.filter((topic) => topic.roles.some((role) => activeRoles.includes(role)));
}

function matchTopic(query: string, roles: string[]) {
  const normalizedQuery = query.toLowerCase();
  const queryWords = new Set(normalizedQuery.match(/[a-z0-9]+/g) ?? []);
  const available = visibleTopics(roles);
  let best: HelpTopic | undefined;
  let bestScore = 0;
  for (const topic of available) {
    const score = topic.keywords.reduce(
      (total, keyword) => {
        const normalizedKeyword = keyword.toLowerCase();
        const matched = normalizedKeyword.includes(" ")
          ? normalizedQuery.includes(normalizedKeyword)
          : queryWords.has(normalizedKeyword);
        return total + (matched ? normalizedKeyword.length + 2 : 0);
      },
      0
    );
    if (score > bestScore) {
      best = topic;
      bestScore = score;
    }
  }
  return best;
}

export function HelpdeskCopilot({ roles }: { roles: string[] }) {
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<HelpMessage[]>([]);
  const nextMessageId = useRef(0);
  const activeRoles = roles.length > 0 ? roles : ["public"];
  const availableTopics = visibleTopics(activeRoles);
  const recommendations = availableTopics.slice(0, 3);

  function answerQuestion(text: string) {
    const topic = matchTopic(text, roles);
    const userMessageId = nextMessageId.current + 1;
    nextMessageId.current += 2;
    setMessages((current) => [
      ...current,
      { id: userMessageId, sender: "user", text },
      {
        id: userMessageId + 1,
        sender: "copilot",
        text: topic
          ? `Happy to help! ${topic.answer}`
          : `I’m not quite sure about that one yet. Here are some example questions you can ask as a ${roleLabel(activeRoles)}:`,
        topic,
        suggestedPrompts: topic
          ? undefined
          : availableTopics.flatMap((item) => item.prompts).slice(0, 5)
      }
    ]);
    setQuestion("");
  }

  function submitQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = question.trim();
    if (text) answerQuestion(text);
  }

  return (
    <div className="helpdesk-widget">
      {open && (
        <section
          aria-label="Deposit360 Helpdesk Copilot"
          aria-modal="false"
          className="helpdesk-panel"
          role="dialog"
        >
          <header className="helpdesk-header">
            <div>
              <strong>Helpdesk Copilot</strong>
              <span>{roleLabel(activeRoles)} · friendly workflow guidance</span>
            </div>
            <button
              aria-label="Close Helpdesk Copilot"
              className="helpdesk-close"
              onClick={() => setOpen(false)}
              type="button"
            >
              ×
            </button>
          </header>
          <div className="helpdesk-messages" aria-live="polite">
            {messages.length === 0 ? (
              <article className="helpdesk-message helpdesk-reply">
                <strong>Hi there! What can I help you with?</strong>
                <p>Ask me a question in your own words, or choose a suggested topic. I’ll point you to the right steps. I can guide you, but I can’t make decisions or verify bank documents.</p>
              </article>
            ) : messages.map((message) => (
              <article
                className={`helpdesk-message ${message.sender === "user" ? "helpdesk-question" : "helpdesk-reply"}`}
                key={message.id}
              >
                <p>{message.text}</p>
                {message.topic && (
                  <>
                    <ol>
                      {message.topic.steps.map((step) => <li key={step}>{step}</li>)}
                    </ol>
                    {message.topic.href && (
                      <Link className="helpdesk-action" href={message.topic.href}>
                        {message.topic.linkLabel}
                      </Link>
                    )}
                  </>
                )}
                {message.suggestedPrompts && message.suggestedPrompts.length > 0 && (
                  <div className="helpdesk-suggested-questions" aria-label="Example questions for your role">
                    {message.suggestedPrompts.map((prompt) => (
                      <button key={prompt} onClick={() => answerQuestion(prompt)} type="button">
                        {prompt}
                      </button>
                    ))}
                  </div>
                )}
              </article>
            ))}
          </div>
          {messages.length === 0 && (
            <div className="helpdesk-suggestions" aria-label="Suggested help topics">
              {recommendations.map((topic) => (
                <button key={topic.title} onClick={() => answerQuestion(topic.prompts[0])} type="button">
                  {topic.prompts[0]}
                </button>
              ))}
            </div>
          )}
          <form className="helpdesk-form" onSubmit={submitQuestion}>
            <label className="visually-hidden" htmlFor="helpdesk-question">Ask for help</label>
            <input
              autoComplete="off"
              id="helpdesk-question"
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask how to complete a task…"
              value={question}
            />
            <button aria-label="Send question" className="button button-primary" disabled={!question.trim()} type="submit">
              Send
            </button>
          </form>
          <p className="helpdesk-disclaimer">Guided answers are based on the demo workflow, not live AI or bank verification.</p>
        </section>
      )}
      <button
        aria-expanded={open}
        aria-haspopup="dialog"
        className="helpdesk-launcher"
        onClick={() => setOpen((current) => !current)}
        type="button"
      >
        <svg aria-hidden="true" className="helpdesk-bot-icon" viewBox="0 0 24 24" fill="none">
          <path d="M12 3.5v2.2M9.6 3.5h4.8" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
          <rect x="4" y="6.5" width="16" height="13" rx="4" stroke="currentColor" strokeWidth="1.7" />
          <path d="M8.2 12h.1m7.4 0h.1M9 15.5c1.7 1.2 4.3 1.2 6 0" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          <path d="M2.5 11v4m19-4v4" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
        </svg>
        Helpdesk Copilot
      </button>
    </div>
  );
}
