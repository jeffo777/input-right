import React, { useState, useEffect } from 'react';

export interface LeadData {
  name: string;
  inquiry: string;
  email: string;
  phone: string;
}

interface LeadCaptureFormProps {
  initialData: any;
  onSubmit: (data: LeadData) => void;
  onCancel: () => void;
}

export const LeadCaptureForm: React.FC<LeadCaptureFormProps> = ({ initialData, onSubmit, onCancel }) => {
  const [formData, setFormData] = useState<LeadData>({
      name: '',
      inquiry: '',
      email: '',
      phone: ''
  });

      useEffect(() => {
    console.log("LeadCaptureForm received initialData:", initialData);
    // The actual lead data is inside the 'payload' property, which is a JSON string
    const leadDetails = JSON.parse(initialData.payload);
    setFormData({
      name: leadDetails.name || '',
      inquiry: leadDetails.inquiry || '',
      email: leadDetails.email || '',
      phone: leadDetails.phone || ''
    });
  }, [initialData]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { id, value } = e.target;
    setFormData((prevData) => ({ ...prevData, [id]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <div className="lead-form-overlay">
      <div className="lead-form-container">
        <h2>Verify Your Information</h2>
        <p>Please confirm the details below are correct before we send them to the team.</p>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="name">Full Name</label>
            <input type="text" id="name" value={formData.name} onChange={handleChange} />
          </div>
          <div className="form-group">
            <label htmlFor="inquiry">Your Inquiry</label>
            <textarea id="inquiry" value={formData.inquiry} onChange={handleChange} rows={3}></textarea>
          </div>
          <div className="form-group">
            <label htmlFor="email">Email Address (Required)</label>
            <input type="email" id="email" value={formData.email} onChange={handleChange} required />
          </div>
          <div className="form-group">
            <label htmlFor="phone">Phone Number (Optional)</label>
            <input type="tel" id="phone" value={formData.phone} onChange={handleChange} />
          </div>
          <div className="form-actions">
            <button type="button" className="button-secondary" onClick={onCancel}>Cancel</button>
            <button type="submit" className="button-primary">Looks Good, Send It</button>
          </div>
        </form>
      </div>
    </div>
  );
};