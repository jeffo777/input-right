import React, { useState, useEffect } from 'react';

export interface LeadData {
  name: string;
  inquiry: string;
  contactDetail: string;
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
      contactDetail: ''
  });

  // This hook now correctly populates the state from the prop
  useEffect(() => {
    setFormData({
      name: initialData.name || '',
      inquiry: initialData.inquiry || '',
      contactDetail: initialData.contact_detail || '' // Read from snake_case
    });
  }, [initialData]);

  // This handler is now simplified and works for all fields
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
            <label htmlFor="contactDetail">Contact (Email/Phone)</label>
            <input type="text" id="contactDetail" value={formData.contactDetail} onChange={handleChange} />
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