import { z } from "zod";

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
