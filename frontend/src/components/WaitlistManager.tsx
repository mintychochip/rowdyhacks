import { useState, useEffect } from 'react';
import {
  Box,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Button,
  Badge,
  Text,
  Flex,
  useToast,
  Spinner,
  HStack,
  VStack,
} from '@chakra-ui/react';
import { ArrowUpIcon } from '@chakra-ui/icons';
import { WaitlistEntry } from '../types/registration';
import { getWaitlist, promoteFromWaitlist } from '../services/api';

interface WaitlistManagerProps {
  hackathonId: string;
}

export function WaitlistManager({ hackathonId }: WaitlistManagerProps) {
  const [waitlist, setWaitlist] = useState<WaitlistEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [promoting, setPromoting] = useState(false);
  const toast = useToast();

  useEffect(() => {
    loadWaitlist();
  }, [hackathonId]);

  async function loadWaitlist() {
    try {
      const data = await getWaitlist(hackathonId);
      setWaitlist(data.waitlist);
    } catch (error) {
      toast({
        title: 'Error loading waitlist',
        status: 'error',
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
      toast({
        title: 'Offer sent!',
        description: `Promoted position #1 (expires ${new Date(result.offer_expires_at).toLocaleString()})`,
        status: 'success',
        duration: 5000,
      });
      loadWaitlist(); // Refresh
    } catch (error) {
      toast({
        title: 'Failed to promote',
        description: error instanceof Error ? error.message : 'Unknown error',
        status: 'error',
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
        <VStack align="start" spacing={1}>
          <Text fontSize="lg" fontWeight="bold">
            Waitlist ({waitlist.length} people)
          </Text>
          <Text fontSize="sm" color="gray.600">
            First in line gets the next available spot
          </Text>
        </VStack>
        <Button
          leftIcon={<ArrowUpIcon />}
          colorScheme="blue"
          onClick={handlePromote}
          isLoading={promoting}
          isDisabled={waitlist.length === 0}
        >
          Promote #1 to Offered
        </Button>
      </Flex>

      {waitlist.length === 0 ? (
        <Text color="gray.500" textAlign="center" py={8}>
          Waitlist is empty
        </Text>
      ) : (
        <Table size="sm">
          <Thead>
            <Tr>
              <Th>Position</Th>
              <Th>Name</Th>
              <Th>Email</Th>
              <Th>Registered</Th>
              <Th>Shirt Size</Th>
              <Th>Declines</Th>
            </Tr>
          </Thead>
          <Tbody>
            {waitlist.map((entry) => (
              <Tr key={entry.id}>
                <Td>
                  <Badge colorScheme={entry.position === 1 ? 'green' : 'gray'}>
                    #{entry.position}
                  </Badge>
                </Td>
                <Td fontWeight="medium">{entry.user_name}</Td>
                <Td fontSize="sm">{entry.user_email}</Td>
                <Td fontSize="sm">
                  {new Date(entry.registered_at).toLocaleDateString()}
                </Td>
                <Td>{entry.t_shirt_size || '-'}</Td>
                <Td>
                  {entry.declined_count > 0 && (
                    <Badge colorScheme="orange">{entry.declined_count}</Badge>
                  )}
                </Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      )}
    </Box>
  );
}
