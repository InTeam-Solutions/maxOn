const randomFallback = () => `id-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;

export const generateId = () => {
  if (typeof globalThis !== 'undefined') {
    const cryptoApi = (globalThis as typeof globalThis & { crypto?: Crypto }).crypto;
    if (cryptoApi?.randomUUID) {
      return cryptoApi.randomUUID();
    }
  }
  return randomFallback();
};

