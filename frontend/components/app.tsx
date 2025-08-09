'use client';

import { LeadCaptureForm } from '@/src/LeadCaptureForm';
import { useState } from 'react';
import { Room } from 'livekit-client';
import { motion } from 'motion/react';
import { LiveKitRoom, RoomAudioRenderer, StartAudio } from '@livekit/components-react';
import { toastAlert } from '@/components/alert-toast';import { SessionView } from '@/components/session-view';
import { Toaster } from '@/components/ui/sonner';
import { Welcome } from '@/components/welcome';
import useConnectionDetails from '@/hooks/useConnectionDetails';
import type { AppConfig } from '@/lib/types';
import { LiveKitSessionManager } from './livekit-session-manager';

const MotionWelcome = motion.create(Welcome);

// A global variable to hold the room object for the form submission handler.
// This is a pragmatic approach for the MVP.
let room_instance: Room | null = null;

interface AppProps {
  appConfig: AppConfig;
  livekitUrl?: string;
  apiUrl?: string;
}

export function App({ appConfig, livekitUrl, apiUrl }: AppProps) {
  const [sessionStarted, setSessionStarted] = useState(false);
  const { connectionDetails, refreshConnectionDetails } = useConnectionDetails({ livekitUrl, apiUrl });
  const [isFormVisible, setIsFormVisible] = useState(false);
  const [leadData, setLeadData] = useState(null);

  const onDisconnected = () => {
    console.log(`[${new Date().toISOString()}] APP: Disconnected from room.`);
    setSessionStarted(false);
    refreshConnectionDetails();
    room_instance = null; // Clean up the global room instance
  };

  const onMediaDevicesError = (error: Error) => {
    toastAlert({
      title: 'Encountered an error with your media devices',
      description: `${error.name}: ${error.message}`,
    });
  };

  const handleFormSubmit = async (data: any) => {
    if (!room_instance || !room_instance.localParticipant) {
      console.error("Room instance not available for RPC.");
      return;
    }
    try {
      const payload = JSON.stringify(data);
      await room_instance.localParticipant.performRpc({
        destinationIdentity: "contractor-leads-bot-agent",
        method: "submit_lead_form",
        payload: payload,
      });
      toastAlert({
        title: 'Sent!',
        description: 'Your information has been sent to the team.',
      });
    } catch (e) {
      console.error('Failed to send RPC to agent:', e);
      toastAlert({
        title: 'Error',
        description: 'Could not send your information. Please try again.',
      });
    }
    setIsFormVisible(false);
    setLeadData(null);
  };

  const handleFormCancel = () => {
    setIsFormVisible(false);
    setLeadData(null);
  };

  return (
    <>
      <MotionWelcome
        key="welcome"
        startButtonText={appConfig.startButtonText}
        onStartCall={() => setSessionStarted(true)}
        disabled={sessionStarted || !connectionDetails}
        initial={{ opacity: 0 }}
        animate={{ opacity: sessionStarted ? 0 : 1 }}
        transition={{ duration: 0.5, ease: 'linear', delay: sessionStarted ? 0 : 0.5 }}
      />

            {sessionStarted && connectionDetails && (
                <LiveKitRoom
          serverUrl={connectionDetails.serverUrl}
          token={connectionDetails.participantToken}
          audio={true}
          onConnected={(room) => {
            console.log(`[${new Date().toISOString()}] APP: LiveKitRoom connected.`);
            room_instance = room;
          }}
          onDisconnected={onDisconnected}
          onError={onMediaDevicesError}
          style={{ height: '100dvh' }}
        >
          {/* Audio components now correctly placed inside the provider */}
          <RoomAudioRenderer />
          <StartAudio label="Start Audio" />

          <motion.div
            key="session-view-wrapper"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, ease: 'linear', delay: 0.5 }}
          >
            <SessionView appConfig={appConfig} />
          </motion.div>

          <LiveKitSessionManager 
            appConfig={appConfig} 
            onDisplayForm={(data) => {
              setLeadData(data);
              setIsFormVisible(true);
            }} 
          />

          {isFormVisible && leadData && (
            <LeadCaptureForm
              initialData={leadData as any}
              onSubmit={handleFormSubmit}
              onCancel={handleFormCancel}
            />
          )}
        </LiveKitRoom>
      )}

      <Toaster />
      </>
  );
}