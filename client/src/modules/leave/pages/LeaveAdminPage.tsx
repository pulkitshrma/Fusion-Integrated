import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Button, Card, Container, Group, NumberInput, Select, Stack, Table,
  Text, TextInput, Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { errorMessage, http } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCalendars, useLeaveMutation, usePolicies, useSla, useWorkflow } from "../api/hooks";

const CATEGORIES = ["CL", "RH", "SCL", "EL", "COL", "VL"].map((v) => ({ value: v, label: v }));
const STEP_TYPES = [
  { value: "unit_head", label: "Unit Head" },
  { value: "establishment", label: "Establishment" },
  { value: "sanction", label: "Sanctioning Authority" },
];

export default function LeaveAdminPage() {
  const policies = usePolicies();
  const calendars = useCalendars();
  const workflow = useWorkflow();
  const sla = useSla();
  const reports = useQuery({
    queryKey: ["leave", "reports"],
    queryFn: async () => (await http.get("/leave/admin/reports")).data,
  });
  const createCalendar = useLeaveMutation("/leave/admin/calendars");
  const publishCalendar = useLeaveMutation("/leave/admin/calendars/:id/publish");
  const createWorkflow = useLeaveMutation("/leave/admin/workflow");
  const createSla = useLeaveMutation("/leave/admin/sla");
  const updatePolicy = useLeaveMutation("/leave/admin/policies/:id", "patch");
  const offlineSanction = useLeaveMutation("/leave/admin/offline-sanction");
  const maintainRecord = useLeaveMutation("/leave/admin/records/:id", "patch");

  const [calName, setCalName] = useState("");
  const [calYear, setCalYear] = useState<number | string>(new Date().getFullYear());
  const [calKind, setCalKind] = useState<string | null>("holiday");
  const [calDates, setCalDates] = useState("");
  const [wfCategory, setWfCategory] = useState<string | null>("CL");
  const [wfUnit, setWfUnit] = useState("");
  const [wfRole, setWfRole] = useState("");
  const [wfSequence, setWfSequence] = useState<number | string>(1);
  const [wfType, setWfType] = useState<string | null>("unit_head");
  const [wfAssignee, setWfAssignee] = useState<number | string>("");
  const [wfAssigneeRole, setWfAssigneeRole] = useState("");
  const [slaTask, setSlaTask] = useState("awaiting_unit_head");
  const [reminder, setReminder] = useState<number | string>(24);
  const [escalation, setEscalation] = useState<number | string>(48);
  const [escalationUser, setEscalationUser] = useState<number | string>("");
  const [offlineUser, setOfflineUser] = useState<number | string>("");
  const [offlineCategory, setOfflineCategory] = useState<string | null>("CL");
  const [offlineStart, setOfflineStart] = useState("");
  const [offlineEnd, setOfflineEnd] = useState("");
  const [offlinePurpose, setOfflinePurpose] = useState("");
  const [offlineReference, setOfflineReference] = useState("");
  const [offlineDate, setOfflineDate] = useState("");
  const [recordId, setRecordId] = useState<number | string>("");
  const [recordPurpose, setRecordPurpose] = useState("");
  const [recordReason, setRecordReason] = useState("");

  function success(message: string) {
    notifications.show({ color: "green", title: "Saved", message });
    void policies.refetch(); void calendars.refetch();
    void workflow.refetch(); void sla.refetch(); void reports.refetch();
  }
  function fail(error: unknown) {
    notifications.show({ color: "red", title: "Could not save", message: errorMessage(error) });
  }

  if (policies.error || calendars.error || workflow.error || sla.error || reports.error) {
    return <Container size="xl"><ErrorState error={policies.error || calendars.error || workflow.error || sla.error || reports.error} /></Container>;
  }

  return (
    <Container size="xl">
      <PageHeader title="Leave Administration" subtitle="Policies, calendars, approval routes and SLA thresholds" />
      <Stack gap="lg">
        <Card withBorder padding="lg">
          <Title order={4} mb="sm">Leave policies</Title>
          <Table.ScrollContainer minWidth={620}>
            <Table striped>
              <Table.Thead><Table.Tr><Table.Th>Category</Table.Th><Table.Th>Annual entitlement</Table.Th><Table.Th>Carry forward</Table.Th><Table.Th>Applicability</Table.Th><Table.Th>Medical evidence</Table.Th><Table.Th>Action</Table.Th></Table.Tr></Table.Thead>
              <Table.Tbody>
                {(policies.data?.results ?? []).map((p: Record<string, unknown>) => (
                  <Table.Tr key={String(p.id)}>
                    <Table.Td>{String(p.category)}</Table.Td>
                    <Table.Td>{String(p.annual_entitlement)}</Table.Td>
                    <Table.Td>{p.carry_forward ? "Yes" : "No"}</Table.Td>
                    <Table.Td>{p.faculty_only ? "Faculty only" : p.non_faculty_only ? "Non-faculty only" : "All eligible employees"}</Table.Td>
                    <Table.Td>{p.medical_evidence_required ? "Required" : "Not required"}</Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                      <Button size="xs" variant="light" onClick={() => {
                        const value = window.prompt("New annual entitlement", String(p.annual_entitlement));
                        if (value !== null && Number.isFinite(Number(value))) {
                          updatePolicy.mutate({ id: Number(p.id), body: { annual_entitlement: value } },
                            { onSuccess: () => success("Policy updated"), onError: fail });
                        }
                      }}>Edit entitlement</Button>
                      <Button size="xs" variant="subtle" onClick={() => updatePolicy.mutate({
                        id: Number(p.id), body: { medical_evidence_required: !Boolean(p.medical_evidence_required) },
                      }, { onSuccess: () => success("Evidence policy updated"), onError: fail })}>Toggle evidence</Button>
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        </Card>

        <Card withBorder padding="lg">
          <Title order={4} mb="sm">Publish holiday / RH calendar</Title>
          <Stack gap="xs">
            <TextInput label="Calendar name" value={calName} onChange={(e) => setCalName(e.currentTarget.value)} />
            <Group grow>
              <NumberInput label="Year" value={calYear} onChange={setCalYear} min={2000} max={2100} />
              <Select label="Calendar type" data={[{ value: "holiday", label: "Closed holidays" }, { value: "rh", label: "Restricted holidays" }]} value={calKind} onChange={setCalKind} />
            </Group>
            <TextareaPlaceholder value={calDates} onChange={setCalDates} />
            <Group justify="flex-end">
              <Button loading={createCalendar.isPending} disabled={!calName.trim() || !calKind || !calDates.trim()}
                onClick={() => createCalendar.mutate({ body: { name: calName, year: Number(calYear), kind: calKind, dates: calDates.split(",").map((v) => v.trim()).filter(Boolean) } },
                  { onSuccess: () => { success("Calendar created; publish it to make it effective."); setCalName(""); setCalDates(""); }, onError: fail })}>
                Create calendar
              </Button>
            </Group>
          </Stack>
          <Table mt="md">
            <Table.Thead><Table.Tr><Table.Th>Calendar</Table.Th><Table.Th>Year</Table.Th><Table.Th>Type</Table.Th><Table.Th>Status</Table.Th><Table.Th /></Table.Tr></Table.Thead>
            <Table.Tbody>
              {(calendars.data?.results ?? []).map((item: Record<string, unknown>) => (
                <Table.Tr key={String(item.id)}>
                  <Table.Td>{String(item.name)}</Table.Td><Table.Td>{String(item.year)}</Table.Td>
                  <Table.Td>{String(item.kind)}</Table.Td><Table.Td>{item.is_published ? "Published" : "Draft"}</Table.Td>
                  <Table.Td>{!item.is_published && <Button size="xs" onClick={() => publishCalendar.mutate({ id: Number(item.id) }, { onSuccess: () => success("Calendar published"), onError: fail })}>Publish</Button>}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>

        <Card withBorder padding="lg">
          <Title order={4} mb="sm">Approval route configuration</Title>
          <Text size="xs" c="dimmed" mb="sm">Configure an explicit assignee for every category, unit and applicant role. Missing routes fail closed.</Text>
          <Stack gap="xs">
            <Group grow>
              <Select label="Leave category" data={CATEGORIES} value={wfCategory} onChange={setWfCategory} />
              <Select label="Workflow step" data={STEP_TYPES} value={wfType} onChange={setWfType} />
            </Group>
            <Group grow>
              <TextInput label="Organizational unit (blank = default)" value={wfUnit} onChange={(e) => setWfUnit(e.currentTarget.value)} />
              <TextInput label="Applicant role / designation (blank = default)" value={wfRole} onChange={(e) => setWfRole(e.currentTarget.value)} />
            </Group>
            <Group grow>
              <NumberInput label="Sequence" min={1} value={wfSequence} onChange={setWfSequence} />
              <NumberInput label="Assignee user ID" min={1} value={wfAssignee} onChange={setWfAssignee} />
              <TextInput label="Assignee role label" value={wfAssigneeRole} onChange={(e) => setWfAssigneeRole(e.currentTarget.value)} />
            </Group>
            <Group justify="flex-end">
              <Button loading={createWorkflow.isPending} disabled={!wfCategory || !wfType || !wfAssignee}
                onClick={() => createWorkflow.mutate({ body: { category: wfCategory, organizational_unit: wfUnit, designation: wfRole, sequence: Number(wfSequence), step_type: wfType, assignee_user_id: Number(wfAssignee), assignee_role: wfAssigneeRole, is_active: true } },
                  { onSuccess: () => success("Workflow step created"), onError: fail })}>
                Add workflow step
              </Button>
            </Group>
          </Stack>
          <Table mt="md">
            <Table.Thead><Table.Tr><Table.Th>Category</Table.Th><Table.Th>Unit / role</Table.Th><Table.Th>Step</Table.Th><Table.Th>Assignee</Table.Th></Table.Tr></Table.Thead>
            <Table.Tbody>
              {(workflow.data?.results ?? []).map((step: Record<string, unknown>) => (
                <Table.Tr key={String(step.id)}>
                  <Table.Td>{String(step.category)}</Table.Td><Table.Td>{String(step.organizational_unit || "Default")} / {String(step.designation || "Any role")}</Table.Td>
                  <Table.Td>{String(step.sequence)} · {String(step.step_type)}</Table.Td><Table.Td>{String(step.assignee_user_id)}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>

        <Card withBorder padding="lg">
          <Title order={4} mb="sm">SLA reminder and escalation thresholds</Title>
          <Stack gap="xs">
            <TextInput label="Task type (e.g. awaiting_unit_head, lifecycle:extension)" value={slaTask} onChange={(e) => setSlaTask(e.currentTarget.value)} />
            <Group grow>
              <NumberInput label="Reminder after (hours)" min={1} value={reminder} onChange={setReminder} />
              <NumberInput label="Escalate after (hours)" min={2} value={escalation} onChange={setEscalation} />
              <NumberInput label="Escalation recipient user ID" min={1} value={escalationUser} onChange={setEscalationUser} />
            </Group>
            <Group justify="flex-end">
              <Button loading={createSla.isPending} disabled={!slaTask.trim() || Number(escalation) <= Number(reminder) || !escalationUser}
                onClick={() => createSla.mutate({ body: { task_type: slaTask, reminder_after_hours: Number(reminder), escalate_after_hours: Number(escalation), escalation_assignee_user_id: Number(escalationUser), is_active: true } },
                  { onSuccess: () => success("SLA configuration created"), onError: fail })}>
                Add SLA configuration
              </Button>
            </Group>
          </Stack>
          <Table mt="md">
            <Table.Thead><Table.Tr><Table.Th>Task</Table.Th><Table.Th>Reminder</Table.Th><Table.Th>Escalation</Table.Th><Table.Th>Recipient</Table.Th></Table.Tr></Table.Thead>
            <Table.Tbody>
              {(sla.data?.results ?? []).map((item: Record<string, unknown>) => (
                <Table.Tr key={String(item.id)}><Table.Td>{String(item.task_type)}</Table.Td>
                  <Table.Td>{String(item.reminder_after_hours)}h</Table.Td><Table.Td>{String(item.escalate_after_hours)}h</Table.Td>
                  <Table.Td>{String(item.escalation_assignee_user_id ?? "—")}</Table.Td></Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>


        <Card withBorder padding="lg">
          <Title order={4} mb="sm">Record an already-sanctioned offline leave</Title>
          <Text size="xs" c="dimmed" mb="sm">Synchronizes an existing authorized sanction; this does not create a new approval.</Text>
          <Stack gap="xs">
            <Group grow>
              <NumberInput label="Employee user ID" min={1} value={offlineUser} onChange={setOfflineUser} />
              <Select label="Category" data={CATEGORIES} value={offlineCategory} onChange={setOfflineCategory} />
            </Group>
            <Group grow>
              <TextInput label="Start date" type="date" value={offlineStart} onChange={(e) => setOfflineStart(e.currentTarget.value)} />
              <TextInput label="End date" type="date" value={offlineEnd} onChange={(e) => setOfflineEnd(e.currentTarget.value)} />
            </Group>
            <TextInput label="Purpose" value={offlinePurpose} onChange={(e) => setOfflinePurpose(e.currentTarget.value)} />
            <Group grow>
              <TextInput label="Sanction reference number" value={offlineReference} onChange={(e) => setOfflineReference(e.currentTarget.value)} />
              <TextInput label="Sanction date" type="date" value={offlineDate} onChange={(e) => setOfflineDate(e.currentTarget.value)} />
            </Group>
            <Group justify="flex-end">
              <Button loading={offlineSanction.isPending}
                disabled={!offlineUser || !offlineCategory || !offlineStart || !offlineEnd || !offlinePurpose.trim() || !offlineReference.trim() || !offlineDate}
                onClick={() => offlineSanction.mutate({ body: {
                  user_id: Number(offlineUser), category: offlineCategory,
                  start_date: offlineStart, end_date: offlineEnd, purpose: offlinePurpose,
                  sanction_reference: offlineReference, sanction_date: offlineDate,
                } }, { onSuccess: () => success("Offline sanction synchronized"), onError: fail })}>
                Record offline sanction
              </Button>
            </Group>
          </Stack>
        </Card>


        <Card withBorder padding="lg">
          <Title order={4} mb="sm">Maintain an authorized leave record</Title>
          <Text size="xs" c="dimmed" mb="sm">Only descriptive fields are editable here. Dates, category, status and balances remain governed by their workflows and ledger.</Text>
          <Stack gap="xs">
            <NumberInput label="Application reference ID" min={1} value={recordId} onChange={setRecordId} />
            <TextareaPlaceholder value={recordPurpose} onChange={setRecordPurpose} />
            <TextInput label="Correction reason (required)" value={recordReason} onChange={(e) => setRecordReason(e.currentTarget.value)} />
            <Group justify="flex-end">
              <Button loading={maintainRecord.isPending} disabled={!recordId || !recordPurpose.trim() || !recordReason.trim()}
                onClick={() => maintainRecord.mutate({ id: Number(recordId), body: {
                  purpose: recordPurpose, correction_note: recordReason,
                } }, { onSuccess: () => success("Leave record corrected"), onError: fail })}>
                Save correction
              </Button>
            </Group>
          </Stack>
        </Card>

        <Card withBorder padding="lg">
          <Title order={4} mb="sm">Operational report</Title>
          <Text size="sm">Applications by status</Text>
          {(reports.data?.applications_by_status ?? []).map((row: { status: string; count: number }) => (
            <Group key={row.status} justify="space-between"><Text size="sm">{row.status.replaceAll("_", " ")}</Text><Text fw={600}>{row.count}</Text></Group>
          ))}
          <Text size="sm" mt="sm">Applications by category</Text>
          {(reports.data?.applications_by_category ?? []).map((row: { category: string; count: number }) => (
            <Group key={row.category} justify="space-between"><Text size="sm">{row.category}</Text><Text fw={600}>{row.count}</Text></Group>
          ))}
        </Card>
      </Stack>
    </Container>
  );
}

function TextareaPlaceholder({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return <TextInput label="Dates (comma-separated YYYY-MM-DD)" placeholder="2026-01-01, 2026-01-26" value={value} onChange={(e) => onChange(e.currentTarget.value)} />;
}
