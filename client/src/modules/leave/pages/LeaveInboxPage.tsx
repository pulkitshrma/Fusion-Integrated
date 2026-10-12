import { Badge, Button, Card, Container, Group, Stack, Table, Text, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useLeaveInbox, useLeaveMutation, useLifecycleInbox, useLifecycleSubstituteInbox,
  useSubstituteInbox,
} from "../api/hooks";
import type { LeaveApplication, LifecycleRequest } from "../api/types";

export default function LeaveInboxPage() {
  const inbox = useLeaveInbox();
  const substitute = useSubstituteInbox();
  const lifecycle = useLifecycleInbox();
  const lifecycleSubstitute = useLifecycleSubstituteInbox();
  const decide = useLeaveMutation("/leave/applications/:id/decision");
  const respond = useLeaveMutation("/leave/applications/:id/substitute-response");
  const decideLifecycle = useLeaveMutation("/leave/lifecycle/:id/decision");
  const respondLifecycle = useLeaveMutation("/leave/lifecycle/:id/substitute-response");

  function act(mutation: ReturnType<typeof useLeaveMutation>, id: number,
               body: Record<string, unknown>, title: string) {
    mutation.mutate({ id, body }, {
      onSuccess: () => {
        notifications.show({ color: "green", title, message: "The workflow has been updated." });
        void inbox.refetch(); void substitute.refetch();
        void lifecycle.refetch(); void lifecycleSubstitute.refetch();
      },
      onError: (e) => notifications.show({ color: "red", title: "Action failed", message: errorMessage(e) }),
    });
  }

  const firstError = inbox.error || substitute.error || lifecycle.error || lifecycleSubstitute.error;
  if (firstError) return <Container size="xl"><ErrorState error={firstError} /></Container>;

  return (
    <Container size="xl">
      <PageHeader title="Leave Approvals" subtitle="Your assigned decisions and substitute requests" />
      <Stack gap="lg">
        <Card withBorder padding="lg">
          <Title order={4} mb="sm">Applications assigned to me</Title>
          <Table.ScrollContainer minWidth={760}>
            <Table striped>
              <Table.Thead><Table.Tr><Table.Th>Ref</Table.Th><Table.Th>Employee ID</Table.Th>
                <Table.Th>Category</Table.Th><Table.Th>Dates</Table.Th><Table.Th>Purpose</Table.Th><Table.Th>Decision</Table.Th></Table.Tr></Table.Thead>
              <Table.Tbody>
                {(inbox.data?.results ?? []).map((app: LeaveApplication) => (
                  <Table.Tr key={app.id}>
                    <Table.Td>#{app.id}</Table.Td><Table.Td>{app.user_id}</Table.Td>
                    <Table.Td>{app.category}</Table.Td><Table.Td>{app.start_date} – {app.end_date}</Table.Td>
                    <Table.Td>{app.purpose}</Table.Td>
                    <Table.Td>
                      <Group gap={4}>
                        {app.status === "awaiting_unit_head" && (app.category === "CL" || app.category === "RH") ? <>
                          <Button size="xs" onClick={() => act(decide, app.id, { outcome: "approve" }, "Leave approved")}>Approve</Button>
                          <Button size="xs" color="red" variant="light" onClick={() => act(decide, app.id, { outcome: "reject" }, "Leave rejected")}>Reject</Button>
                        </> : app.status === "awaiting_unit_head" ? <>
                          <Button size="xs" onClick={() => act(decide, app.id, { outcome: "recommended" }, "Recommended")}>Recommend</Button>
                          <Button size="xs" color="orange" variant="light" onClick={() => act(decide, app.id, { outcome: "not_recommended" }, "Not recommended")}>Not recommend</Button>
                        </> : app.status === "awaiting_establishment" ? (
                          <Button size="xs" onClick={() => act(decide, app.id, { outcome: "route" }, "Routed to sanctioning authority")}>Route onward</Button>
                        ) : <>
                          <Button size="xs" onClick={() => act(decide, app.id, { outcome: "approve" }, "Leave approved")}>Approve</Button>
                          <Button size="xs" color="red" variant="light" onClick={() => act(decide, app.id, { outcome: "reject" }, "Leave rejected")}>Reject</Button>
                        </>}
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
          {!inbox.isPending && !inbox.data?.results?.length && <Text c="dimmed" size="sm">No applications are assigned to you.</Text>}
        </Card>

        <Card withBorder padding="lg">
          <Title order={4} mb="sm">Substitute consent</Title>
          {(substitute.data?.results ?? []).map((app: LeaveApplication) => (
            <Group key={app.id} justify="space-between" py="xs">
              <Stack gap={0}>
                <Text fw={600}>Application #{app.id} · {app.category}</Text>
                <Text size="xs" c="dimmed">{app.start_date} – {app.end_date}</Text>
              </Stack>
              <Group gap="xs">
                <Button size="xs" onClick={() => act(respond, app.id, { accept: true }, "Substitute accepted")}>Accept</Button>
                <Button size="xs" color="red" variant="light" onClick={() => act(respond, app.id, { accept: false, note: "Unable to take responsibility" }, "Substitute declined")}>Decline</Button>
              </Group>
            </Group>
          ))}
          {!substitute.isPending && !substitute.data?.results?.length && <Text c="dimmed" size="sm">No substitute requests.</Text>}
        </Card>

        <Card withBorder padding="lg">
          <Title order={4} mb="sm">Cancellation, extension and resumption reviews</Title>
          {(lifecycle.data?.results ?? []).map((req: LifecycleRequest) => (
            <Group key={req.id} justify="space-between" py="xs">
              <Stack gap={0}>
                <Text fw={600}>#{req.id} · {req.kind} · application #{req.application_id}</Text>
                <Text size="xs" c="dimmed">{req.requested_start_date ?? req.actual_resumption_date ?? "—"} – {req.requested_end_date ?? "—"}</Text>
              </Stack>
              <Group gap="xs">
                <Button size="xs" onClick={() => act(decideLifecycle, req.id, { approve: true }, "Lifecycle request approved")}>Approve / recommend</Button>
                <Button size="xs" color="red" variant="light" onClick={() => act(decideLifecycle, req.id, { approve: false }, "Lifecycle request rejected")}>Reject / not recommend</Button>
              </Group>
            </Group>
          ))}
          {!lifecycle.isPending && !lifecycle.data?.results?.length && <Text c="dimmed" size="sm">No lifecycle requests assigned to you.</Text>}
        </Card>

        <Card withBorder padding="lg">
          <Title order={4} mb="sm">Extension substitute consent</Title>
          {(lifecycleSubstitute.data?.results ?? []).map((req: LifecycleRequest) => (
            <Group key={req.id} justify="space-between" py="xs">
              <Text size="sm">Extension #{req.id} · application #{req.application_id}</Text>
              <Group gap="xs">
                <Button size="xs" onClick={() => act(respondLifecycle, req.id, { accept: true }, "Extension substitute accepted")}>Accept</Button>
                <Button size="xs" color="red" variant="light" onClick={() => act(respondLifecycle, req.id, { accept: false, note: "Unable to take responsibility" }, "Extension substitute declined")}>Decline</Button>
              </Group>
            </Group>
          ))}
          {!lifecycleSubstitute.isPending && !lifecycleSubstitute.data?.results?.length && <Text c="dimmed" size="sm">No extension substitute requests.</Text>}
        </Card>
      </Stack>
    </Container>
  );
}
