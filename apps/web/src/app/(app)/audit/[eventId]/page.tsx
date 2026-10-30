import { WorkflowCenter } from "@/components/workflow-center";

export default async function AuditEventPage({
  params
}: {
  params: Promise<{ eventId: string }>;
}) {
  const { eventId } = await params;
  return <WorkflowCenter mode="audit" recordId={eventId} />;
}