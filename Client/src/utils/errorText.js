// The Server sends error codes (FOLDER_NOT_FOUND...); the screen shows the translated text for that code.
// An unknown code falls back to the Server's own message, so nothing is ever blank.

export function errorText(t, error) {
  return t(`errors.${error.code}`, { defaultValue: error.message });
}

// For AI errors the Server's message says what exactly happened (which provider, how long to wait),
// so it is shown under the translated text. It names models and providers, so it stays as sent.
const DETAILED_CODES = ["AI_UNAVAILABLE", "AI_RATE_LIMITED"];

export function errorDetail(error) {
  return DETAILED_CODES.includes(error.code) && error.message ? error.message : null;
}
