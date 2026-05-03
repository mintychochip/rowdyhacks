import { useState, useEffect } from 'react';
import {
  Box,
  Text,
  Button,
  HStack,
  VStack,
  Badge,
  Alert,
  createToaster,
} from '@chakra-ui/react';
import { acceptOffer, declineOffer } from '../services/api';

const toaster = createToaster({
  placement: 'bottom-end',
  overlap: true,
  gap: 8,
});

interface OfferBannerProps {
  registrationId: string;
  offerExpiresAt: string;
  hackathonName: string;
  onStatusChange: () => void;
}

export function OfferBanner({
  registrationId,
  offerExpiresAt,
  hackathonName,
  onStatusChange,
}: OfferBannerProps) {
  const [timeLeft, setTimeLeft] = useState('');
  const [loading, setLoading] = useState(false);
  const [expired, setExpired] = useState(false);

  useEffect(() => {
    const updateTimer = () => {
      const now = new Date().getTime();
      const expires = new Date(offerExpiresAt).getTime();
      const diff = expires - now;

      if (diff <= 0) {
        setTimeLeft('Expired');
        setExpired(true);
        return;
      }

      const hours = Math.floor(diff / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      setTimeLeft(`${hours}h ${minutes}m`);
    };

    updateTimer();
    const interval = setInterval(updateTimer, 60000); // Update every minute

    return () => clearInterval(interval);
  }, [offerExpiresAt]);

  async function handleAccept() {
    setLoading(true);
    try {
      await acceptOffer(registrationId);
      toaster.create({
        title: "You're in!",
        description: `You've been accepted to ${hackathonName}`,
        type: 'success',
        duration: 5000,
      });
      onStatusChange();
    } catch (error) {
      toaster.create({
        title: 'Failed to accept',
        description: error instanceof Error ? error.message : 'Spot may no longer be available',
        type: 'error',
        duration: 3000,
      });
    } finally {
      setLoading(false);
    }
  }

  async function handleDecline() {
    setLoading(true);
    try {
      await declineOffer(registrationId);
      toaster.create({
        title: 'Offer declined',
        description: 'You\'ve been returned to the waitlist',
        type: 'info',
        duration: 3000,
      });
      onStatusChange();
    } catch (error) {
      toaster.create({
        title: 'Failed to decline',
        type: 'error',
        duration: 3000,
      });
    } finally {
      setLoading(false);
    }
  }

  if (expired) {
    return (
      <Alert.Root status="warning" borderRadius="md">
        <Alert.Indicator />
        <Text>This offer has expired. You've been returned to the waitlist.</Text>
      </Alert.Root>
    );
  }

  return (
    <Box
      p={5}
      bg="green.50"
      borderRadius="md"
      borderWidth={2}
      borderColor="green.300"
    >
      <VStack align="stretch" gap={4}>
        <HStack justify="space-between">
          <Box>
            <Text fontSize="lg" fontWeight="bold" color="green.800">
              Spot Available: {hackathonName}
            </Text>
            <Text fontSize="sm" color="gray.600">
              A spot opened up and you're next on the waitlist!
            </Text>
          </Box>
          <Badge colorScheme="red" fontSize="md" px={3} py={1}>
            Expires in: {timeLeft}
          </Badge>
        </HStack>

        <Alert.Root status="info" borderRadius="md">
          <Alert.Indicator />
          <Text fontSize="sm">
            You have 24 hours to accept this offer. If you don't respond, the spot will be offered to the next person.
          </Text>
        </Alert.Root>

        <HStack gap={3}>
          <Button
            colorScheme="green"
            size="lg"
            flex={1}
            onClick={handleAccept}
            loading={loading}
          >
            Accept Spot
          </Button>
          <Button
            variant="outline"
            size="lg"
            onClick={handleDecline}
            loading={loading}
            disabled={loading}
          >
            Decline
          </Button>
        </HStack>
      </VStack>
    </Box>
  );
}
