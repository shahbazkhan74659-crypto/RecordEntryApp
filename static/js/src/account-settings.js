import { z } from "zod";
import { postForm } from "./lib/api.js";
import { bindModalDismiss, lockBodyScroll, unlockBodyScroll } from "./lib/modal-dismiss.js";
import { setStepVisibility } from "./lib/step-toggle.js";

const usernameSchema = z
  .object({
    newUsername: z.string().min(1, "Enter a username.").max(150, "Too long (max 150 characters)."),
    confirmUsername: z.string().min(1, "Confirm your new username."),
  })
  .refine((data) => data.newUsername === data.confirmUsername, { message: "Usernames do not match." });

const passwordSchema = z
  .object({
    oldPassword: z.string().min(1, "Enter your current password."),
    newPassword: z.string().min(8, "Password must be at least 8 characters."),
    confirmPassword: z.string().min(1, "Confirm your new password."),
  })
  .refine((data) => data.newPassword === data.confirmPassword, { message: "Passwords do not match." });

const emailSchema = z.string().min(1, "Enter an email address.").email("Enter a valid email address.");
const otpSchema = z.string().trim().regex(/^\d{6}$/, "Enter the 6-digit code.");

document.addEventListener("DOMContentLoaded", () => {
  const modal = document.querySelector("#account-settings-modal");
  const openButton = document.querySelector("#open-account-settings");
  if (!modal || !openButton) return;

  const changeUsernameUrl = modal.dataset.changeUsernameUrl;
  const changePasswordUrl = modal.dataset.changePasswordUrl;
  const requestOtpUrl = modal.dataset.requestOtpUrl;
  const verifyOtpUrl = modal.dataset.verifyOtpUrl;
  const revertEmailUrl = modal.dataset.revertEmailUrl;
  const originalUsername = modal.dataset.username;

  // --- Username section ---
  const usernameForm = modal.querySelector("#account-username-section .account-section-form");
  const usernameSuccess = modal.querySelector("#account-username-success");
  const usernameSuccessValue = modal.querySelector("#account-username-success-value");
  const usernameError = modal.querySelector("#account-username-error");
  const newUsernameInput = modal.querySelector("#account-new-username");
  const confirmUsernameInput = modal.querySelector("#account-confirm-username");
  const usernameSaveBtn = modal.querySelector("#account-username-save");
  const usernameAgainBtn = modal.querySelector("#account-username-again");

  let usernameChanged = false;

  function resetUsernameSection() {
    newUsernameInput.value = "";
    confirmUsernameInput.value = "";
    usernameError.textContent = "";
    usernameForm.hidden = false;
    usernameSuccess.hidden = true;
    usernameChanged = false;
  }

  usernameSaveBtn.addEventListener("click", async () => {
    usernameError.textContent = "";
    const result = usernameSchema.safeParse({
      newUsername: newUsernameInput.value,
      confirmUsername: confirmUsernameInput.value,
    });
    if (!result.success) {
      usernameError.textContent = result.error.issues[0].message;
      return;
    }

    const { ok, data } = await postForm(changeUsernameUrl, { new_username: result.data.newUsername });
    if (!ok) {
      usernameError.textContent = data.error || "Could not change the username.";
      return;
    }

    usernameSuccessValue.textContent = data.username;
    usernameForm.hidden = true;
    usernameSuccess.hidden = false;
    usernameChanged = true;
  });

  usernameAgainBtn.addEventListener("click", () => {
    newUsernameInput.value = "";
    confirmUsernameInput.value = "";
    usernameForm.hidden = false;
    usernameSuccess.hidden = true;
  });

  // --- Password section ---
  const passwordForm = modal.querySelector("#account-password-section .account-section-form");
  const passwordSuccess = modal.querySelector("#account-password-success");
  const passwordError = modal.querySelector("#account-password-error");
  const oldPasswordInput = modal.querySelector("#account-old-password");
  const newPasswordInput = modal.querySelector("#account-new-password");
  const confirmPasswordInput = modal.querySelector("#account-confirm-password");
  const passwordSaveBtn = modal.querySelector("#account-password-save");
  const passwordAgainBtn = modal.querySelector("#account-password-again");

  let originalPassword = null;
  let currentPassword = null;

  function resetPasswordSection() {
    oldPasswordInput.value = "";
    newPasswordInput.value = "";
    confirmPasswordInput.value = "";
    passwordError.textContent = "";
    passwordForm.hidden = false;
    passwordSuccess.hidden = true;
    originalPassword = null;
    currentPassword = null;
  }

  passwordSaveBtn.addEventListener("click", async () => {
    passwordError.textContent = "";
    const result = passwordSchema.safeParse({
      oldPassword: oldPasswordInput.value,
      newPassword: newPasswordInput.value,
      confirmPassword: confirmPasswordInput.value,
    });
    if (!result.success) {
      passwordError.textContent = result.error.issues[0].message;
      return;
    }

    const { ok, data } = await postForm(changePasswordUrl, {
      old_password: result.data.oldPassword,
      new_password: result.data.newPassword,
      confirm_password: result.data.confirmPassword,
    });
    if (!ok) {
      passwordError.textContent = data.error || "Could not change the password.";
      return;
    }

    if (originalPassword === null) originalPassword = result.data.oldPassword;
    currentPassword = result.data.newPassword;

    passwordForm.hidden = true;
    passwordSuccess.hidden = false;
  });

  passwordAgainBtn.addEventListener("click", () => {
    oldPasswordInput.value = "";
    newPasswordInput.value = "";
    confirmPasswordInput.value = "";
    passwordForm.hidden = false;
    passwordSuccess.hidden = true;
  });

  // --- Email section ---
  const emailCheckbox = modal.querySelector("#account-email-checkbox");
  const emailTick = modal.querySelector("#account-email-tick");
  const emailRequestStep = modal.querySelector("#account-email-request-step");
  const emailOtpStep = modal.querySelector("#account-email-otp-step");
  const emailConfirmedStep = modal.querySelector("#account-email-confirmed-step");
  const newEmailInput = modal.querySelector("#account-new-email");
  const emailRequestError = modal.querySelector("#account-email-request-error");
  const emailSendBtn = modal.querySelector("#account-email-send");
  const emailOtpTarget = modal.querySelector("#account-email-otp-target");
  const emailOtpInput = modal.querySelector("#account-email-otp");
  const emailOtpNotice = modal.querySelector("#account-email-otp-notice");
  const emailOtpError = modal.querySelector("#account-email-otp-error");
  const emailVerifyBtn = modal.querySelector("#account-email-verify");
  const emailResendBtn = modal.querySelector("#account-email-resend");
  const emailConfirmedValue = modal.querySelector("#account-email-confirmed-value");
  const emailAgainBtn = modal.querySelector("#account-email-again");

  let emailChanged = false;
  let pendingNewEmail = "";

  function showEmailStep(step) {
    setStepVisibility(
      { "enter-email": emailRequestStep, "enter-otp": emailOtpStep, confirmed: emailConfirmedStep },
      step,
    );
  }

  function resetEmailSection() {
    emailCheckbox.checked = false;
    newEmailInput.value = "";
    emailOtpInput.value = "";
    emailRequestError.textContent = "";
    emailOtpNotice.textContent = "";
    emailOtpError.textContent = "";
    emailTick.hidden = true;
    showEmailStep(null);
    emailChanged = false;
    pendingNewEmail = "";
  }

  emailCheckbox.addEventListener("change", () => {
    if (emailCheckbox.checked) {
      showEmailStep(emailChanged ? "confirmed" : "enter-email");
    } else {
      showEmailStep(null);
    }
  });

  emailSendBtn.addEventListener("click", async () => {
    emailRequestError.textContent = "";
    const result = emailSchema.safeParse(newEmailInput.value);
    if (!result.success) {
      emailRequestError.textContent = result.error.issues[0].message;
      return;
    }

    const { ok, data } = await postForm(requestOtpUrl, { new_email: result.data });
    if (!ok) {
      emailRequestError.textContent = data.error || "Could not send the verification code.";
      return;
    }

    pendingNewEmail = result.data;
    emailOtpTarget.textContent = pendingNewEmail;
    emailOtpInput.value = "";
    emailOtpNotice.textContent = "";
    emailOtpError.textContent = "";
    showEmailStep("enter-otp");
  });

  emailResendBtn.addEventListener("click", async () => {
    emailOtpNotice.textContent = "";
    emailOtpError.textContent = "";
    const { ok, data } = await postForm(requestOtpUrl, { new_email: pendingNewEmail });
    if (!ok) {
      emailOtpError.textContent = data.error || "Could not resend the verification code.";
      return;
    }
    emailOtpNotice.textContent = "A new code has been sent.";
  });

  emailVerifyBtn.addEventListener("click", async () => {
    emailOtpError.textContent = "";
    const result = otpSchema.safeParse(emailOtpInput.value);
    if (!result.success) {
      emailOtpError.textContent = result.error.issues[0].message;
      return;
    }

    const { ok, data } = await postForm(verifyOtpUrl, { new_email: pendingNewEmail, otp: result.data });
    if (!ok) {
      emailOtpError.textContent = data.error || "Could not verify the code.";
      return;
    }

    emailChanged = true;
    emailConfirmedValue.textContent = data.email;
    emailTick.hidden = false;
    showEmailStep("confirmed");
  });

  emailAgainBtn.addEventListener("click", () => {
    newEmailInput.value = "";
    emailRequestError.textContent = "";
    showEmailStep("enter-email");
  });

  // --- Modal open/close, Cancel revert, Done ---

  function resetAllSections() {
    resetUsernameSection();
    resetPasswordSection();
    resetEmailSection();
  }

  function hasPendingChanges() {
    return usernameChanged || emailChanged || currentPassword !== null;
  }

  async function revertPendingChanges() {
    const tasks = [];
    if (usernameChanged) {
      tasks.push(postForm(changeUsernameUrl, { new_username: originalUsername }));
    }
    if (originalPassword !== null && currentPassword !== null) {
      tasks.push(postForm(changePasswordUrl, {
        old_password: currentPassword,
        new_password: originalPassword,
        confirm_password: originalPassword,
        revert: "1",
      }));
    }
    if (emailChanged) {
      tasks.push(postForm(revertEmailUrl, {}));
    }
    if (tasks.length > 0) {
      await Promise.allSettled(tasks);
    }
  }

  function openModal() {
    modal.classList.add("visible");
    lockBodyScroll();
  }

  function closeModal() {
    modal.classList.remove("visible");
    unlockBodyScroll();
  }

  openButton.addEventListener("click", () => {
    resetAllSections();
    openModal();
  });

  async function handleCancel() {
    if (hasPendingChanges()) {
      await revertPendingChanges();
    }
    resetAllSections();
    closeModal();
  }

  modal.querySelector("#account-settings-cancel").addEventListener("click", handleCancel);

  bindModalDismiss(modal, handleCancel);

  modal.querySelector("#account-settings-done").addEventListener("click", () => {
    const shouldReload = usernameChanged;
    resetAllSections();
    closeModal();
    if (shouldReload) {
      window.location.reload();
    }
  });
});
