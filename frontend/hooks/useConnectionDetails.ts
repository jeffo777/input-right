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
         const contractorId = "bob-the-builder-123";
         const apiUrl = "http://127.0.0.1:8001"; // Our Python backend
         const livekitUrl = "wss://contractor-leads-bot-d8djm77w.livekit.cloud"; // Your LiveKit URL
         // --- END OF HARDCODED VALUES ---

         const resp = await fetch(`${apiUrl}/api/token`, {
           method: 'POST',
           headers: { 'Content-Type': 'application/json' },
           body: JSON.stringify({ contractor_id: contractorId }),
         });

         if (!resp.ok) {
             const errorBody = await resp.text();
             throw new Error(`Failed to fetch token: ${resp.statusText}. Body: ${errorBody}`);
         }

         const data = await resp.json();

         const details: ConnectionDetails = {
           serverUrl: livekitUrl,
           roomName: contractorId,
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