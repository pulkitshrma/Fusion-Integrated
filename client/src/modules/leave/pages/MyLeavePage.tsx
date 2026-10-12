import { useState, type FormEvent } from "react";
import {
  Alert, Badge, Button, Card, Checkbox, Container, Group, Select, Stack,
  Table, Text, TextInput, Textarea, Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { ErrorState } from "../../../ui/components/ErrorState";
import {
  useLeaveBalances, useLeaveLedger, useLeaveMutation, useMyLeave, useMyLifecycle,
} from "../api/hooks";
import type { LeaveApplication, LeaveCategory } from "../api/types";

const CATEGORIES: { value: LeaveCategory; label: string }[] = [
  { value: "CL", label: "Casual Leave (CL)" },
  { value: "RH", label: "Restricted Holiday (RH)" },
  { value: "SCL", label: "Special Casual Leave (SCL)" },
  { value: "EL", label: "Earned Leave (EL)" },
  { value: "COL", label: "Commuted Leave (COL)" },
  { value: "VL", label: "Vacation Leave (VL)" },
];

export default function MyLeavePage() {
  const applications = useMyLeave();
  const balances = useLeaveBalances();
  const ledger = useLeaveLedger();
  const lifecycle = useMyLifecycle();
  const apply = useLeaveMutation("/leave/applications/apply");
  const withdraw = useLeaveMutation("/leave/applications/:id/withdraw");
  const cancel = useLeaveMutation("/leave/applications/:id/cancel");
  const extend = useLeaveMutation("/leave/applications/:id/extend");
  const resume = useLeaveMutation("/leave/applications/:id/resumption");
  const withdrawLifecycle = useLeaveMutation("/leave/lifecycle/:id/withdraw");
  const replaceSubstitute = useLeaveMutation("/leave/applications/:id/substitute-replacement");
  const replaceLifecycleSubstitute = useLeaveMutation("/leave/lifecycle/:id/substitute-replacement");

  const [category, setCategory] = useState<string | null>("CL");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [halfDay, setHalfDay] = useState<string | null>("");
  const [purpose, setPurpose] = useState("");
  const [substitute, setSubstitute] = useState("");
  const [station, setStation] = useState(false);
  const [stationDetails, setStationDetails] = useState("");
  const [evidence, setEvidence] = useState("");
  const [extensionSubstitutes, setExtensionSubstitutes] = useState<Record<number, string>>({});
  const [extensionEvidence, setExtensionEvidence] = useState<Record<number, string>>({});
  const [resumptionDetails, setResumptionDetails] = useState<Record<number, string>>({});
  const [replacementIds, setReplacementIds] = useState<Record<number, string>>({});
  const [extensionDates, setExtensionDates] = useState<Record<number, string>>({});
  const [resumptionDates, setResumptionDates] = useState<Record<number, string>>({});

  function done(title: string) {
    notifications.show({ color: "green", title, message: "Your request has been recorded." });
    void applications.refetch();
    void balances.refetch();
    void ledger.refetch();
    void lifecycle.refetch();
  }
  function failed(e: unknown) {
    notifications.show({ color: "red", title: "Request failed", message: errorMessage(e) });
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!category || !start || !end || !purpose.trim()) return;
    apply.mutate({
      body: {
        category, start_date: start, end_date: end, purpose,
        supporting_evidence_reference: evidence,
        half_day: halfDay || "",
        station_leave_required: station,
        station_leave_details: station ? { details: stationDetails } : {},
        ...(substitute.trim() ? { substitute_user_id: Number(substitute) } : {}),
      },
    }, { onSuccess: () => {
      done("Leave application submitted");
      setPurpose(""); setSubstitute(""); setStation(false); setStationDetails(""); setEvidence("");
    }, onError: failed });
  }

  function action(mutation: ReturnType<typeof useLeaveMutation>, id: number,
                  body: Record<string, unknown> = {}, title: string) {
    mutation.mutate({ id, body }, { onSuccess: () => done(title), onError: failed });
  }

  if (applications.error) return <Container size="xl"><ErrorState error={applications.error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader title="My Leave" subtitle="Apply for leave, track decisions and review your leave account" />
      <Stack gap="lg">
        <Card withBorder padding="lg">
          <Title order={4} mb="sm">Apply for leave</Title>
          <form onSubmit={submit}>
            <Stack gap="sm">
              <Select label="Leave category" data={CATEGORIES} value={category} onChange={setCategory} required />
              <Group grow>
                <TextInput label="Start date" type="date" value={start} onChange={(e) => setStart(e.currentTarget.value)} required />
                <TextInput label="End date" type="date" value={end} onChange={(e) => setEnd(e.currentTarget.value)} required />
              </Group>
              {category === "CL" && (
                <Select label="Half day (optional)" clearable value={halfDay} onChange={setHalfDay}
                  data={[{ value: "first_half", label: "First half" }, { value: "second_half", label: "Second half" }]} />
              )}
              <Textarea label="Purpose / reason" value={purpose} onChange={(e) => setPurpose(e.currentTarget.value)} minRows={2} required />
              {category === "COL" && <TextInput label="Supporting medical evidence reference (if required by policy)" value={evidence} onChange={(e) => setEvidence(e.currentTarget.value)} />}
              <TextInput label="Substitute employee user ID (if required)" value={substitute} onChange={(e) => setSubstitute(e.currentTarget.value)} />
              <Checkbox label="Station Leave required" checked={station} onChange={(e) => setStation(e.currentTarget.checked)} />
              {station && <Textarea label="Station Leave details" value={stationDetails} onChange={(e) => setStationDetails(e.currentTarget.value)} required />}
              <Group justify="flex-end">
                <Button type="submit" loading={apply.isPending}>Submit application</Button>
              </Group>
            </Stack>
          </form>
        </Card>

        <Card withBorder padding="lg">
          <Title order={4} mb="sm">Current balances</Title>
          {balances.error && <Alert color="red">{errorMessage(balances.error)}</Alert>}
          <Table.ScrollContainer minWidth={560}>
            <Table striped>
              <Table.Thead><Table.Tr>
                <Table.Th>Category</Table.Th><Table.Th>Year</Table.Th><Table.Th>Credited</Table.Th>
                <Table.Th>Carry forward</Table.Th><Table.Th>Consumed</Table.Th><Table.Th>Available</Table.Th>
              </Table.Tr></Table.Thead>
              <Table.Tbody>
                {(balances.data?.results ?? []).map((b) => <Table.Tr key={b.category}>
                  <Table.Td>{b.category}</Table.Td><Table.Td>{b.year}</Table.Td>
                  <Table.Td>{b.credited}</Table.Td><Table.Td>{b.carried_forward}</Table.Td>
                  <Table.Td>{b.consumed}</Table.Td><Table.Td fw={700}>{b.available}</Table.Td>
                </Table.Tr>)}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        </Card>

        <Card withBorder padding="lg">
          <Title order={4} mb="sm">My applications</Title>
          {applications.isPending && <Text c="dimmed">Loading applications…</Text>}
          <Table.ScrollContainer minWidth={760}>
            <Table striped>
              <Table.Thead><Table.Tr>
                <Table.Th>Ref</Table.Th><Table.Th>Category</Table.Th><Table.Th>Period</Table.Th>
                <Table.Th>Days</Table.Th><Table.Th>Status</Table.Th><Table.Th>Actions</Table.Th>
              </Table.Tr></Table.Thead>
              <Table.Tbody>
                {(applications.data?.results ?? []).map((app: LeaveApplication) => (
                  <Table.Tr key={app.id}>
                    <Table.Td>#{app.id}</Table.Td><Table.Td>{app.category}</Table.Td>
                    <Table.Td>{app.start_date} – {app.end_date}</Table.Td>
                    <Table.Td>{app.requested_days}</Table.Td>
                    <Table.Td><Badge variant="light">{app.status.replaceAll("_", " ")}</Badge></Table.Td>
                    <Table.Td>
                      <Group gap={4} wrap="nowrap">
                        {["awaiting_substitute","applicant_action_required","awaiting_unit_head","awaiting_establishment","awaiting_sanction"].includes(app.status)
                          && <Button size="xs" color="gray" variant="light" onClick={() => action(withdraw, app.id, {}, "Application withdrawn")}>Withdraw</Button>}
                        {app.status === "applicant_action_required" && app.substitute_response === "declined" && <>
                          <TextInput size="xs" aria-label="Replacement substitute user ID" placeholder="New substitute ID"
                            value={replacementIds[app.id] ?? ""}
                            onChange={(e) => setReplacementIds((v) => ({ ...v, [app.id]: e.currentTarget.value }))} />
                          <Button size="xs" variant="light" disabled={!replacementIds[app.id]}
                            onClick={() => action(replaceSubstitute, app.id, { substitute_user_id: Number(replacementIds[app.id]) }, "Replacement nominated")}>Replace</Button>
                        </>}
                        {app.status === "approved" && <>
                          {app.start_date > new Date().toISOString().slice(0, 10) &&
                            <Button size="xs" color="gray" variant="light" onClick={() => action(cancel, app.id, { details: "Employee requested cancellation" }, "Cancellation requested")}>Cancel</Button>}
                          {["EL", "COL", "VL"].includes(app.category) && <>
                            <TextInput size="xs" type="date" aria-label="New extension end date" value={extensionDates[app.id] ?? ""}
                              onChange={(e) => setExtensionDates((v) => ({ ...v, [app.id]: e.currentTarget.value }))} />
                            <TextInput size="xs" aria-label="Extension substitute user ID" placeholder="Substitute ID"
                              value={extensionSubstitutes[app.id] ?? ""}
                              onChange={(e) => setExtensionSubstitutes((v) => ({ ...v, [app.id]: e.currentTarget.value }))} />
                            {app.category === "COL" && <TextInput size="xs" aria-label="Extension medical evidence reference" placeholder="Medical evidence reference"
                              value={extensionEvidence[app.id] ?? ""}
                              onChange={(e) => setExtensionEvidence((v) => ({ ...v, [app.id]: e.currentTarget.value }))} />}
                            <Button size="xs" variant="light" disabled={!extensionDates[app.id]}
                              onClick={() => action(extend, app.id, {
                                new_end_date: extensionDates[app.id],
                                ...(extensionSubstitutes[app.id] ? { substitute_user_id: Number(extensionSubstitutes[app.id]) } : {}),
                                supporting_evidence_reference: extensionEvidence[app.id] ?? "",
                              }, "Extension requested")}>Extend</Button>
                            <TextInput size="xs" type="date" aria-label="Actual resumption date" value={resumptionDates[app.id] ?? ""}
                              onChange={(e) => setResumptionDates((v) => ({ ...v, [app.id]: e.currentTarget.value }))} />
                            <TextInput size="xs" aria-label="Resumption details" placeholder="Resumption details"
                              value={resumptionDetails[app.id] ?? ""}
                              onChange={(e) => setResumptionDetails((v) => ({ ...v, [app.id]: e.currentTarget.value }))} />
                            <Button size="xs" variant="light" disabled={!resumptionDates[app.id] || !resumptionDetails[app.id]?.trim()}
                              onClick={() => action(resume, app.id, {
                                actual_resumption_date: resumptionDates[app.id], details: resumptionDetails[app.id],
                              }, "Resumption submitted")}>Resume</Button>
                          </>}
                          <Button size="xs" component="a" href={"/api/v1/leave/applications/" + app.id + "/export"} target="_blank" variant="subtle">Print</Button>
                        </>}
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
          {!applications.isPending && !applications.data?.results?.length && <Text c="dimmed" size="sm">No leave applications yet.</Text>}
        </Card>

        <Card withBorder padding="lg">
          <Title order={4} mb="sm">Lifecycle requests</Title>
          {(lifecycle.data?.results ?? []).map((r) => <Group key={r.id} justify="space-between" py={4}>
            <Text size="sm">#{r.id} · {r.kind} · application #{r.application_id}</Text>
            <Group gap="xs">
              <Badge variant="light">{r.status.replaceAll("_", " ")}</Badge>
              {r.status === "applicant_action_required" && r.kind === "extension" && <>
                <TextInput size="xs" aria-label="Replacement extension substitute user ID" placeholder="New substitute ID"
                  value={replacementIds[r.id] ?? ""}
                  onChange={(e) => setReplacementIds((v) => ({ ...v, [r.id]: e.currentTarget.value }))} />
                <Button size="xs" variant="light" disabled={!replacementIds[r.id]}
                  onClick={() => action(replaceLifecycleSubstitute, r.id, { substitute_user_id: Number(replacementIds[r.id]) }, "Extension substitute replaced")}>Replace</Button>
              </>}
              {["pending", "awaiting_substitute", "applicant_action_required"].includes(r.status) &&
                <Button size="xs" color="gray" variant="light"
                  onClick={() => action(withdrawLifecycle, r.id, { note: "Employee withdrew pending lifecycle request" }, "Lifecycle request withdrawn")}>Withdraw</Button>}
            </Group>
          </Group>)}
        </Card>

        <Card withBorder padding="lg">
          <Title order={4} mb="sm">Leave account history</Title>
          <Table.ScrollContainer minWidth={600}>
            <Table striped>
              <Table.Thead><Table.Tr><Table.Th>Date</Table.Th><Table.Th>Category</Table.Th>
                <Table.Th>Transaction</Table.Th><Table.Th>Amount</Table.Th><Table.Th>Reference</Table.Th></Table.Tr></Table.Thead>
              <Table.Tbody>
                {(ledger.data?.results ?? []).map((entry) => <Table.Tr key={entry.id}>
                  <Table.Td>{new Date(entry.created_at).toLocaleDateString()}</Table.Td>
                  <Table.Td>{entry.category}</Table.Td><Table.Td>{entry.entry_type}</Table.Td>
                  <Table.Td>{entry.amount}</Table.Td><Table.Td>{entry.reference || "—"}</Table.Td>
                </Table.Tr>)}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        </Card>
      </Stack>
    </Container>
  );
}
