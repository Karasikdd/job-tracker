export type User = {
  id: number;
  email: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
};