import { z } from "zod";
import { postForm } from "./lib/api.js";
import { bindModalDismiss, lockBodyScroll, unlockBodyScroll } from "./lib/modal-dismiss.js";
import { setStepVisibility } from "./lib/step-toggle.js";

const loginSchema = z.object({
  username: z.string().min(1, "Username is required"),
  password: z.string().min(1, "Password is required"),
});

function clearErrors(form) {
  form.querySelectorAll(".field-error").forEach((el) => el.remove());
}

function showErrors(form, error) {
  for (const issue of error.issues) {
    const field = form.querySelector(`[name="${issue.path[0]}"]`);
    if (!field) continue;
    const msg = document.createElement("p");
    msg.className = "field-error";
    msg.textContent = issue.message;
    field.insertAdjacentElement("afterend", msg);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("#login-form");
  if (!form) return;

  form.addEventListener("submit", (event) => {
    clearErrors(form);

    const result = loginSchema.safeParse({
      username: form.username.value,
      password: form.password.value,
    });

    if (!result.success) {
      event.preventDefault();
      showErrors(form, result.error);
    }
  });
});

// --- Forgot Password ---

const forgotEmailSchema = z.string().min(1, "Enter an email address.").email("Enter a valid email address.");
const forgotOtpSchema = z.string().trim().regex(/^\d{6}$/, "Enter the 6-digit code.");
const forgotResetSchema = z
  .object({
    newPassword: z.string().min(8, "Password must be at least 8 characters."),
    confirmPassword: z.string().min(1, "Confirm your new password."),
  })
  .refine((data) => data.newPassword === data.confirmPassword, { message: "Passwords do not match." });

document.addEventListener("DOMContentLoaded", () => {
  const usernameInput = document.querySelector("#id_username");
  const forgotBtn = document.querySelector("#forgot-password-btn");
  const modal = document.querySelector("#forgot-password-modal");
  if (!usernameInput || !forgotBtn || !modal) return;

  const checkUsernameUrl = modal.dataset.checkUsernameUrl;
  const requestOtpUrl = modal.dataset.requestOtpUrl;
  const verifyOtpUrl = modal.dataset.verifyOtpUrl;
  const resetUrl = modal.dataset.resetUrl;

  // Debounced so the button doesn't fire a request on every keystroke.
  let usernameCheckTimer = null;
  usernameInput.addEventListener("input", () => {
    clearTimeout(usernameCheckTimer);
    const value = usernameInput.value.trim();
    if (!value) {
      forgotBtn.disabled = true;
      return;
    }
    usernameCheckTimer = setTimeout(async () => {
      const { ok, data } = await postForm(checkUsernameUrl, { username: value });
      forgotBtn.disabled = !(ok && data.valid);
    }, 400);
  });

  const emailStep = document.querySelector("#forgot-password-email-step");
  const otpStep = document.querySelector("#forgot-password-otp-step");
  const resetStep = document.querySelector("#forgot-password-reset-step");

  const emailInput = document.querySelector("#forgot-password-email");
  const emailError = document.querySelector("#forgot-password-email-error");
  const emailSendBtn = document.querySelector("#forgot-password-email-send");
  const emailCancelBtn = document.querySelector("#forgot-password-email-cancel");

  const otpTarget = document.querySelector("#forgot-password-otp-target");
  const otpInput = document.querySelector("#forgot-password-otp");
  const otpNotice = document.querySelector("#forgot-password-otp-notice");
  const otpError = document.querySelector("#forgot-password-otp-error");
  const otpVerifyBtn = document.querySelector("#forgot-password-otp-verify");
  const otpResendBtn = document.querySelector("#forgot-password-otp-resend");
  const otpCancelBtn = document.querySelector("#forgot-password-otp-cancel");

  const newPasswordInput = document.querySelector("#forgot-password-new");
  const confirmPasswordInput = document.querySelector("#forgot-password-confirm");
  const resetError = document.querySelector("#forgot-password-reset-error");
  const resetSubmitBtn = document.querySelector("#forgot-password-reset-submit");
  const resetCancelBtn = document.querySelector("#forgot-password-reset-cancel");

  let forgotUsername = "";
  let resetToken = "";

  function showStep(step) {
    setStepVisibility({ email: emailStep, otp: otpStep, reset: resetStep }, step);
  }

  function resetModalState() {
    resetToken = "";
    emailInput.value = "";
    emailError.textContent = "";
    otpInput.value = "";
    otpNotice.textContent = "";
    otpError.textContent = "";
    newPasswordInput.value = "";
    confirmPasswordInput.value = "";
    resetError.textContent = "";
    showStep("email");
  }

  function closeModal() {
    modal.classList.remove("visible");
    unlockBodyScroll();
    resetModalState();
  }

  forgotBtn.addEventListener("click", () => {
    if (forgotBtn.disabled) return;
    forgotUsername = usernameInput.value.trim();
    resetModalState();
    modal.classList.add("visible");
    lockBodyScroll();
  });

  emailCancelBtn.addEventListener("click", closeModal);
  otpCancelBtn.addEventListener("click", closeModal);
  resetCancelBtn.addEventListener("click", closeModal);
  bindModalDismiss(modal, closeModal);

  emailSendBtn.addEventListener("click", async () => {
    emailError.textContent = "";
    const result = forgotEmailSchema.safeParse(emailInput.value);
    if (!result.success) {
      emailError.textContent = result.error.issues[0].message;
      return;
    }

    const { ok, data } = await postForm(requestOtpUrl, { username: forgotUsername, email: result.data });
    if (!ok) {
      emailError.textContent = data.error || "Could not send the verification code.";
      return;
    }

    otpTarget.textContent = result.data;
    otpInput.value = "";
    otpNotice.textContent = "";
    otpError.textContent = "";
    showStep("otp");
  });

  otpResendBtn.addEventListener("click", async () => {
    otpNotice.textContent = "";
    otpError.textContent = "";
    const { ok, data } = await postForm(requestOtpUrl, { username: forgotUsername, email: emailInput.value });
    if (!ok) {
      otpError.textContent = data.error || "Could not resend the verification code.";
      return;
    }
    otpNotice.textContent = "A new code has been sent.";
  });

  otpVerifyBtn.addEventListener("click", async () => {
    otpError.textContent = "";
    const result = forgotOtpSchema.safeParse(otpInput.value);
    if (!result.success) {
      otpError.textContent = result.error.issues[0].message;
      return;
    }

    const { ok, data } = await postForm(verifyOtpUrl, { username: forgotUsername, otp: result.data });
    if (!ok) {
      otpError.textContent = data.error || "Could not verify the code.";
      return;
    }

    resetToken = data.reset_token;
    newPasswordInput.value = "";
    confirmPasswordInput.value = "";
    resetError.textContent = "";
    showStep("reset");
  });

  resetSubmitBtn.addEventListener("click", async () => {
    resetError.textContent = "";
    const result = forgotResetSchema.safeParse({
      newPassword: newPasswordInput.value,
      confirmPassword: confirmPasswordInput.value,
    });
    if (!result.success) {
      resetError.textContent = result.error.issues[0].message;
      return;
    }

    const { ok, data } = await postForm(resetUrl, {
      reset_token: resetToken,
      new_password: result.data.newPassword,
      confirm_password: result.data.confirmPassword,
    });
    if (!ok) {
      resetError.textContent = data.error || "Could not reset the password.";
      return;
    }

    window.location.href = "/login/";
  });
});
