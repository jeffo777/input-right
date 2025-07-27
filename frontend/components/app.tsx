'use client';

import { LeadCaptureForm } from '@/src/LeadCaptureForm';
import { LocalParticipant } from 'livekit-client';
import { useEffect, useMemo, useState } from 'react';
import { Room, RoomEvent, Participant } from 'livekit-client';
import { motion } from 'motion/react';
import { RoomAudioRenderer, RoomContext, StartAudio } from '@livekit/components-react';
import { toastAlert } from '@/components/alert-toast';
import { SessionView } from '@/components/session-view';
import { Toaster } from '@/components/ui/sonner';
import { Welcome } from '@/components/welcome';
import useConnectionDetails from '@/hooks/useConnectionDetails';
import type { AppConfig } from '@/lib/types';

const MotionWelcome = motion.create(Welcome);
const MotionSessionView = motion.create(SessionView);

interface AppProps {
  appConfig: AppConfig;
  livekitUrl?: string;
  apiUrl?: string;
}

export function App({ appConfig, livekitUrl, apiUrl }: AppProps) {
  const room = useMemo(() => new Room(), []);
  const [sessionStarted, setSessionStarted] = useState(false);
  const { connectionDetails, refreshConnectionDetails } = useConnectionDetails({ livekitUrl, apiUrl });
const [isFormVisible, setIsFormVisible] = useState(false);
const [leadData, setLeadData] = useState(null);

const handleFormSubmit = async (data: any) => {
  console.log('Form submitted with data:', data);
  if (!room) return;

  // Find the agent participant in the room
  const agentParticipant = Array.from(room.remoteParticipants.values()).find(
    (p) => p.identity === 'contractor-leads-bot-agent'
  );

  if (agentParticipant) {
    try {
      // Send the RPC command 'submit_lead_form' to the agent
      await room.localParticipant.publishData(
        new TextEncoder().encode(JSON.stringify(data)),
        {
          destinationIdentities: [agentParticipant.identity],
          topic: 'submit_lead_form',
          reliable: true,
        }
      );
      console.log('Successfully sent submit_lead_form RPC to agent');
    } catch (e) {
      console.error('Failed to send RPC to agent:', e);
      toastAlert({
        title: 'Error',
        description: 'Could not send your information. Please try again.',
      });
    }
  } else {
    console.error('Could not find agent participant to send RPC to.');
    toastAlert({
        title: 'Error',
        description: 'Could not find the agent. Please try again.',
      });
  }

  // Hide the form and clear the data after submission
  setIsFormVisible(false);
  setLeadData(null);
};

const handleFormCancel = () => {
  console.log('Form cancelled');
  setIsFormVisible(false);
  setLeadData(null);
};

  useEffect(() => {
    const onDisconnected = () => {
      setSessionStarted(false);
      refreshConnectionDetails();
    };
    const onMediaDevicesError = (error: Error) => {
      toastAlert({
        title: 'Encountered an error with your media devices',
        description: `${error.name}: ${error.message}`,
      });
    };

// --- START OF NEW LOGGING ---
  const onParticipantConnected = (participant: Participant) => {
      console.log("A participant connected:", {
          identity: participant.identity,
          sid: participant.sid,
          kind: participant.kind,
          metadata: participant.metadata,
      });
  };
  // --- END OF NEW LOGGING ---

    room.on(RoomEvent.MediaDevicesError, onMediaDevicesError);
    room.on(RoomEvent.Disconnected, onDisconnected);
    return () => {
      room.off(RoomEvent.Disconnected, onDisconnected);
      room.off(RoomEvent.MediaDevicesError, onMediaDevicesError);
    };
  }, [room, refreshConnectionDetails]);

useEffect(() => {
  if (!room || !room.localParticipant) return;

  const localParticipant = room.localParticipant;

  // This is the handler function for our RPC method
  const handleDisplayLeadForm = async (payload: unknown, context: any) => {
  console.log('--- RPC DEBUG START ---');
  console.log('Received payload argument:', payload);
  console.log('Received context argument:', context);
  console.log('Type of payload:', typeof payload);
  console.log('--- RPC DEBUG END ---');

  try {
    // We will assume for now the actual JSON string is in the 'payload' property
    // of the first argument. This may be wrong, but the logs will tell us.
    const data = JSON.parse((payload as any).payload);
    setLeadData(data);
    setIsFormVisible(true);
    return "SUCCESS"; 
  } catch (error) {
    console.error('Failed to handle or parse RPC payload:', error);
    throw new Error('Failed to handle or parse payload');
  }
};

  // Register the method with the name the agent is calling
  localParticipant.registerRpcMethod("display_lead_form", handleDisplayLeadForm);

  // Clean up by unregistering the method when the component unmounts
  return () => {
    localParticipant.unregisterRpcMethod("display_lead_form");
  };
}, [room]);

  useEffect(() => {
    let aborted = false;
    if (sessionStarted && room.state === 'disconnected' && connectionDetails) {
      room.connect(connectionDetails.serverUrl, connectionDetails.participantToken)
        .catch((error) => {
          if (aborted) { return; }
          toastAlert({
            title: 'There was an error connecting to the agent',
            description: `${error.name}: ${error.message}`,
          });
        });
    }
    return () => {
      aborted = true;
      room.disconnect();
    };
  }, [room, sessionStarted, connectionDetails]);

  const { startButtonText } = appConfig;

return (
  <>
    <MotionWelcome
      key="welcome"
      startButtonText={startButtonText}
      onStartCall={() => setSessionStarted(true)}
      disabled={sessionStarted || !connectionDetails}
      initial={{ opacity: 0 }}
      animate={{ opacity: sessionStarted ? 0 : 1 }}
      transition={{ duration: 0.5, ease: 'linear', delay: sessionStarted ? 0 : 0.5 }}
    />

    <RoomContext.Provider value={room}>
      <RoomAudioRenderer />
      <StartAudio label="Start Audio" />
      <MotionSessionView
        key="session-view"
        appConfig={appConfig}
        disabled={!sessionStarted}
        sessionStarted={sessionStarted}
        initial={{ opacity: 0 }}
        animate={{ opacity: sessionStarted ? 1 : 0 }}
        transition={{
          duration: 0.5,
          ease: 'linear',
          delay: sessionStarted ? 0.5 : 0,
        }}
      />

      {/* START OF NEW CODE TO ADD */}
      {isFormVisible && leadData && (
  <LeadCaptureForm
    initialData={leadData as any}
    onSubmit={handleFormSubmit}
    onCancel={handleFormCancel}
  />
)}
      {/* END OF NEW CODE TO ADD */}

    </RoomContext.Provider>

    <Toaster />
  </>
);
}