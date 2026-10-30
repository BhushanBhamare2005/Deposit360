import { WorkflowCenter } from "@/components/workflow-center";

export default async function ScrutinyCasePage({
  params
}: {
  params: Promise<{ caseId: string }>;
}) {
  const { caseId } = await params;
  return <WorkflowCenter mode="scrutiny" recordId={caseId} />;
}