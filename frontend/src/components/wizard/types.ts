export interface AboutYouData {
  age: string;
  school: string;
  major: string;
  pronouns: string;
  phone: string;
}

export interface SkillsLinksData {
  skills: string[];
  linkedinUrl: string;
  githubUrl: string;
  resumeUrl: string;
  experienceLevel: string;
}

export interface LogisticsData {
  tshirtSize: string;
  dietaryRestrictions: string;
  emergencyContactName: string;
  emergencyContactPhone: string;
  // New fields
  t_shirt_size?: string | null;
  dietary_restrictions?: string | null;
  special_needs?: string | null;
  school_company?: string | null;
  graduation_year?: number | null;
  experience_level?: string | null;
}

export interface ShortAnswersData {
  whatBuild: string;
  whyParticipate: string;
}
