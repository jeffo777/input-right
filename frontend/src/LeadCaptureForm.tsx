import React, { useState } from 'react';

// Define the structure of the lead data
export interface LeadData {
  name: string;
  inquiry: string;
  contactDetail: string;
}

interface LeadCaptureFormProps {
  initialData: LeadData;
  // Add two new props: functions to handle submit and cancel actions
  onSubmit: (data: LeadData) => void;
  onCancel: () => void;
}

export const LeadCaptureForm: React.FC<LeadCaptureFormProps> = ({ initialData, onSubmit, onCancel }) => {
  // Use React state to manage the form data, initialized with the data from the agent
  const [formData, setFormData] = useState<LeadData>({
    name: initialData.name || '',
    inquiry: initialData.inquiry || '',
    contactDetail: (initialData as any).contact_detail || '' 
});

  // Handler for form input changes
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { id, value } = e.target;
    setFormData((prevData) => ({ ...prevData, [id]: value }));
  };

  // Handler for the form submission
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault(); // Prevent the default browser form submission
    onSubmit(formData); // Call the onSubmit function passed in as a prop
  };

  return (
    <div className="lead-form-overlay">
      <div className="lead-form-container">
        <h2>Verify Your Information</h2>
        <p>Please confirm the details below are correct before we send them to the team.</p>
        {/* Attach the handleSubmit function to the form's onSubmit event */}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="name">Full Name</label>
            {/* The input now reads its value from state and updates state on change */}
            <input type="text" id="name" value={formData.name} onChange={handleChange} />
          </div>
          <div className="form-group">
            <label htmlFor="inquiry">Your Inquiry</label>
            {/* The textarea now reads its value from state and updates state on change */}
            <textarea id="inquiry" value={formData.inquiry} onChange={handleChange} rows={3}></textarea>
          </div>
          <div className="form-group">
            <label htmlFor="contactDetail">Contact (Email/Phone)</label>
            {/* The input now reads its value from state and updates state on change */}
            <input type="text" id="contactDetail" value={formData.contactDetail} onChange={handleChange} />
          </div>
          <div className="form-actions">
            {/* The cancel button now calls the onCancel function */}
            <button type="button" className="button-secondary" onClick={onCancel}>Cancel</button>
            <button type="submit" className="button-primary">Looks Good, Send It</button>
          </div>
        </form>
      </div>
    </div>
  );
};
