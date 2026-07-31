// Shared "show exactly one step, hide the rest" toggler — the same shape
// independently reimplemented as login.js's showStep (forgot-password's
// email/otp/reset steps) and account-settings.js's showEmailStep (its
// enter-email/enter-otp/confirmed steps). `steps` maps a step key to its
// element; every element not matching `active` gets hidden.
export function setStepVisibility(steps, active) {
  Object.entries(steps).forEach(([key, element]) => {
    element.hidden = key !== active;
  });
}
