// Acme's "user database". In your product this is your real user store; the
// only thing Roddy will ever see of it is what YOU put in the visitor token.
//
// `id` is the identity decision that matters most: it becomes the token's
// `sub`, and `sub` decides which conversation the person gets — same sub,
// same conversation, on any device, forever. Use your STABLE internal id.
// Never an email (people change them; then they'd "lose" their history and
// someone inheriting the address would inherit their conversation), and never
// anything a user can edit about themselves.
export const USERS = {
  "emp-1042": {
    id: "emp-1042",
    name: "Ana Torres",
    email: "ana.torres@acme.example",
    role: "Compras",
  },
  "emp-2017": {
    id: "emp-2017",
    name: "Luis Ramos",
    email: "luis.ramos@acme.example",
    role: "Almacén",
  },
};
