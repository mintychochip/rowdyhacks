export interface Registration {
  id: string;
  hackathon_id: string;
  user_id: string;
  status: 'pending' | 'accepted' | 'rejected' | 'waitlisted' | 'offered' | 'checked_in';
  team_name: string | null;
  team_members: string[];
  registered_at: string;
  accepted_at: string | null;
  checked_in_at: string | null;
  offered_at?: string | null;
  offer_expires_at?: string | null;
  declined_count?: number;
  // Registration data fields
  dietary_restrictions: string | null;
  t_shirt_size: string | null;  // Note: model uses t_shirt_size, not shirt_size
  special_needs: string | null;
  experience_level: string | null;
  school_company: string | null;
  graduation_year: number | null;
  // Joined fields
  user_name?: string;
  user_email?: string;
}

export interface WaitlistEntry {
  id: string;
  position: number;
  user_name: string | null;
  user_email: string | null;
  registered_at: string;
  declined_count: number;
  dietary_restrictions: string | null;
  t_shirt_size: string | null;
}

export interface WaitlistResponse {
  waitlist: WaitlistEntry[];
  total: number;
  offset: number;
  limit: number;
}
