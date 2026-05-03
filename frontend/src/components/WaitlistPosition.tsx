import { Box, Text, Badge, HStack, VStack, Progress } from '@chakra-ui/react';

interface WaitlistPositionProps {
  position: number;
  totalWaitlist?: number;
}

export function WaitlistPosition({ position, totalWaitlist }: WaitlistPositionProps) {
  // Calculate progress (inverse - lower position is better)
  const progress = totalWaitlist ? Math.max(0, 100 - (position / totalWaitlist) * 100) : 50;

  return (
    <Box
      p={4}
      bg="orange.50"
      borderRadius="md"
      borderWidth={1}
      borderColor="orange.200"
    >
      <VStack align="stretch" spacing={3}>
        <HStack justify="space-between">
          <Text fontSize="sm" color="orange.800" fontWeight="medium">
            Waitlist Status
          </Text>
          <Badge colorScheme="orange">#{position} in line</Badge>
        </HStack>

        <Progress value={progress} colorScheme="orange" size="sm" borderRadius="full" />

        <Text fontSize="sm" color="gray.600">
          {position === 1
            ? "You're first in line! You'll get the next available spot."
            : position <= 5
            ? `You're in the top ${position} spots. A spot may open up soon!`
            : `There are ${position - 1} people ahead of you. We'll notify you if a spot opens.`}
        </Text>
      </VStack>
    </Box>
  );
}
