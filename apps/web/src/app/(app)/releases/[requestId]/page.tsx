import { WorkflowCenter } from "@/components/workflow-center";

export default async function ReleaseRequestPage({
  params
}: {
  params: Promise<{ requestId: string }>;
}) {
  const { requestId } = await params;
  return <WorkflowCenter mode="releases" recordId={requestId} />;
}