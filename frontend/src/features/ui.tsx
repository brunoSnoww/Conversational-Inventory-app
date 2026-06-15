import type { ReactNode } from 'react';
import { Alert, Center, Container, Paper, Stack, Text, Title } from '@mantine/core';

import { useSyncStatus } from '../sync/PowerSyncProvider';

export function Page({
  title,
  description,
  children,
  narrow,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  narrow?: boolean;
}) {
  const content = (
    <Paper withBorder p="md" radius="md">
      <Stack gap="md">
        <div>
          <Title order={2}>{title}</Title>
          {description ? (
            <Text size="sm" c="dimmed" mt={4}>
              {description}
            </Text>
          ) : null}
        </div>
        {children}
      </Stack>
    </Paper>
  );

  if (narrow) {
    return (
      <Center mih="70vh">
        <Container size="xs" w="100%">
          {content}
        </Container>
      </Center>
    );
  }

  return <Container size="lg" p={0}>{content}</Container>;
}

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Stack gap="sm" mt="md">
      <Title order={4}>{title}</Title>
      {children}
    </Stack>
  );
}

export function Muted({ children }: { children: ReactNode }) {
  return (
    <Text size="sm" c="dimmed">
      {children}
    </Text>
  );
}

export function ErrorText({ children }: { children: ReactNode }) {
  return (
    <Alert color="red" variant="light">
      {children}
    </Alert>
  );
}

export function friendlyError(message: string): string {
  if (/sync|powersync|token|mutation|sqlite|replica|__inventory/i.test(message)) {
    return 'Something went wrong. Please try again.';
  }
  return message;
}

export function useSyncing() {
  const { status, error } = useSyncStatus();
  return {
    syncing: status !== 'ready',
    syncError: error ? friendlyError(error) : null,
    syncStatus: status,
  };
}

export function SyncQuery<T>({
  syncing,
  error,
  data,
  empty,
  children,
}: {
  syncing: boolean;
  error: Error | undefined;
  data: T[] | undefined;
  empty: ReactNode;
  children: (rows: T[]) => ReactNode;
}) {
  if (syncing && !data?.length) {
    return <Muted>Loading…</Muted>;
  }
  if (error) {
    return <ErrorText>{friendlyError(error.message)}</ErrorText>;
  }
  if (!data?.length) {
    return empty;
  }
  return <>{children(data)}</>;
}
