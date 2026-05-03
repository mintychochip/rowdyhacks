import { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Badge,
  Text,
  Flex,
  Spinner,
  HStack,
  VStack,
  Table,
  createToaster,
} from '@chakra-ui/react';
import type { WaitlistEntry } from '../types/registration';
import { getWaitlist, promoteFromWaitlist } from '../services/api';

const toaster = createToaster({
  placement: 'bottom-end',
  overlap: true,
  gap: 8,
});

// Simple SVG arrow up icon
function ArrowUpIcon() {
  return (
    <svg width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 19V5M5 12l7-7 7 7" />
    </svg>
  );
}

interface WaitlistManagerProps {
  hackathonId: string;
}

export function WaitlistManager({ hackathonId }: WaitlistManagerProps) {
  const [waitlist, setWaitlist] = useState<WaitlistEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [promoting, setPromoting] = useState(false);

  useEffect(() => {
    loadWaitlist();
  }, [hackathonId]);

  async function loadWaitlist() {
    try {
      const data = await getWaitlist(hackathonId);
      setWaitlist(data.waitlist);
    } catch (error) {
      toaster.create({
        title: 'Error loading waitlist',
        type: 'error',
        duration: 3000,
      });
    } finally {
      setLoading(false);
    }
  }

  async function handlePromote() {
    setPromoting(true);
    try {
      const result = await promoteFromWaitlist(hackathonId);
      toaster.create({
        title: 'Offer sent!',
        description: `Promoted position #1 (expires ${new Date(result.offer_expires_at).toLocaleString()})`,
        type: 'success',
        duration: 5000,
      });
      loadWaitlist(); // Refresh
    } catch (error) {
      toaster.create({
        title: 'Failed to promote',
        description: error instanceof Error ? error.message : 'Unknown error',
        type: 'error',
        duration: 3000,
      });
    } finally {
      setPromoting(false);
    }
  }

  if (loading) return <Spinner />;

  return (
    <Box>
      <Flex justify="space-between" align="center" mb={4}>
        <VStack align="start" gap={1}>
          <Text fontSize="lg" fontWeight="bold">
            Waitlist ({waitlist.length} people)
          </Text>
          <Text fontSize="sm" color="gray.600">
            First in line gets the next available spot
          </Text>
        </VStack>
        <Button
          colorScheme="blue"
          onClick={handlePromote}
          loading={promoting}
          disabled={waitlist.length === 0}
        >
          <ArrowUpIcon /> Promote #1 to Offered
        </Button>
      </Flex>

      {waitlist.length === 0 ? (
        <Text color="gray.500" textAlign="center" py={8}>
          Waitlist is empty
        </Text>
      ) : (
        <Table.Root size="sm">
          <Table.Header>
            <Table.Row>
              <Table.ColumnHeader>Position</Table.ColumnHeader>
              <Table.ColumnHeader>Name</Table.ColumnHeader>
              <Table.ColumnHeader>Email</Table.ColumnHeader>
              <Table.ColumnHeader>Registered</Table.ColumnHeader>
              <Table.ColumnHeader>Shirt Size</Table.ColumnHeader>
              <Table.ColumnHeader>Declines</Table.ColumnHeader>
            </Table.Row>
          </Table.Header>
          <Table.Body>
            {waitlist.map((entry) => (
              <Table.Row key={entry.id}>
                <Table.Cell>
                  <Badge colorScheme={entry.position === 1 ? 'green' : 'gray'}>
                    #{entry.position}
                  </Badge>
                </Table.Cell>
                <Table.Cell fontWeight="medium">{entry.user_name}</Table.Cell>
                <Table.Cell fontSize="sm">{entry.user_email}</Table.Cell>
                <Table.Cell fontSize="sm">
                  {new Date(entry.registered_at).toLocaleDateString()}
                </Table.Cell>
                <Table.Cell>{entry.t_shirt_size || '-'}</Table.Cell>
                <Table.Cell>
                  {entry.declined_count > 0 && (
                    <Badge colorScheme="orange">{entry.declined_count}</Badge>
                  )}
                </Table.Cell>
              </Table.Row>
            ))}
          </Table.Body>
        </Table.Root>
      )}
    </Box>
  );
}
