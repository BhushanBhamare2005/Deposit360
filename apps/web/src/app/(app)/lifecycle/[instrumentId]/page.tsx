import { WorkflowCenter } from "@/components/workflow-center";

export default async function InstrumentLifecyclePage({
  params
}: {
  params: Promise<{ instrumentId: string }>;
}) {
  const { instrumentId } = await params;
  return <WorkflowCenter mode="lifecycle" recordId={instrumentId} />;
}