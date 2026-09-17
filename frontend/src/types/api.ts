export type User = {
  id: number;
  email: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
};


export type ApplicationStatus =
  | "saved"
  | "applied"
  | "interview"
  | "offer"
  | "rejected";

export type JobApplication = {
  id: number;
  company: string;
  position: string;
  status: ApplicationStatus;
  url: string | null;
  location: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type ApplicationCreate = {
  company: string;
  position: string;
  status?: ApplicationStatus;
  url?: string | null;
  location?: string | null;
  notes?: string | null;
};

export type ApplicationPatch = Partial<ApplicationCreate>;