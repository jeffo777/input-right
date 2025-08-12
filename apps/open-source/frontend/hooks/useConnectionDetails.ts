import { useCallback, useEffect, useState } from 'react';

 export type ConnectionDetails = {
   serverUrl: string;
   roomName: string;
   participantName: string;
   participantToken: string;
 };

 export default function useConnectionDetails() {
   const [connectionDetails, setConnectionDetails] = useState<ConnectionDetails | null>(null);

      const fetchConnectionDetails = useCallback(() => {
     setConnectionDetails(null);
     const getDetails = async () => {
       try {
         // --- START OF HARDCODED VALUES ---
         const businessId = "bob-the-builder-123"; // Renamed variable
         const apiUrl = "http://127.0.0.1:8002"; // The open-source token server
         const livekitUrl = "wss://contractor-leads-bot-d8djm77w.livekit.cloud"; // Your LiveKit URL
         // --- END OF HARDCODED VALUES ---

         // 1. Generate a unique identifier for this specific conversation
         const conversationId = crypto.randomUUID();
         const roomName = `${businessId}_${conversationId}`; // Updated room name construction

         const resp = await fetch(`${apiUrl}/api/token`, {
           method: 'POST',
           headers: { 'Content-Type': 'application/json' },
           // 2. Send both the business_id and the unique roomName to the backend
           body: JSON.stringify({ 
             business_id: businessId, // Renamed field in the request body
             room_name: roomName 
           }),
         });

         if (!resp.ok) {
             const errorBody = await resp.text();
             throw new Error(`Failed to fetch token: ${resp.statusText}. Body: ${errorBody}`);
         }

         const data = await resp.json();

         const details: ConnectionDetails = {
           serverUrl: livekitUrl,
           roomName: roomName, // 3. Use the unique roomName to connect
           participantName: 'Website Visitor',
           participantToken: data.token,
         };
         setConnectionDetails(details);

       } catch (error) {
         console.error('Error fetching connection details:', error);
       }
     };
     getDetails();
   }, []);

   useEffect(() => {
     fetchConnectionDetails();
   }, [fetchConnectionDetails]);

   return { connectionDetails, refreshConnectionDetails: fetchConnectionDetails };
 }