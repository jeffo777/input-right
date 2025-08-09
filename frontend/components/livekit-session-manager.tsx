'use client';

import { useRoomContext } from '@livekit/components-react';
import { useEffect } from 'react';
import type { AppConfig } from '@/lib/types';

interface LiveKitSessionManagerProps {
  appConfig: AppConfig;
  onDisplayForm: (data: any) => void;
}

export const LiveKitSessionManager = ({ appConfig, onDisplayForm }: LiveKitSessionManagerProps) => {
  const room = useRoomContext();

    useEffect(() => {
    // This effect runs once when the component mounts inside a connected LiveKitRoom.
    
    // The <LiveKitRoom> component now handles enabling the microphone via the audio={true} prop.

    // 2. Register the RPC handler for the form
        const handleDisplayLeadForm = async (payload: unknown) => {
      try {
        console.log(`[${new Date().toISOString()}] SESSION_MANAGER: Received display_lead_form RPC with payload:`, payload);
        // The payload is already a parsed JavaScript object, no need for JSON.parse
        const data = payload; 
        onDisplayForm(data); // Pass data up to the App component to manage state
        return "SUCCESS";
      } catch (error) {
        console.error('Failed to handle or parse RPC payload:', error);
        throw new Error('Failed to handle or parse payload');
      }
    };

    room.localParticipant.registerRpcMethod("display_lead_form", handleDisplayLeadForm);

    // 3. Return a cleanup function to unregister the handler when the session ends
    return () => {
      room.localParticipant.unregisterRpcMethod("display_lead_form");
    };
  }, [room, appConfig.isPreConnectBufferEnabled, onDisplayForm]);

  return null; // This component renders no visible UI
};