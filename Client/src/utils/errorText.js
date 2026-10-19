// The Server sends error codes (FOLDER_NOT_FOUND...); the screen shows the translated text for that code.
// An unknown code falls back to the Server's own message, so nothing is ever blank.

export function errorText(t, error) {
  return t(`errors.${error.code}`, { defaultValue: error.message });
}
