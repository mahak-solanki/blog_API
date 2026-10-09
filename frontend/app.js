const API_BASE =
  window.location.port === "5500"
    ? "http://127.0.0.1:8000"
    : "https://blog-api-pe4x.onrender.com";

const $ = (selector) => document.querySelector(selector);

let accessToken = localStorage.getItem("blog_access") || "";
let refreshToken = localStorage.getItem("blog_refresh") || "";
let currentUserId = getUserIdFromToken(accessToken);
let currentUsername = localStorage.getItem("blog_username") || "";
let currentFilter = "all";
const openCommentPosts = new Set();

function formObject(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function getUserIdFromToken(token) {
  try {
    const payloadPart = token.split(".")[1];
    if (!payloadPart) return null;

    const base64 = payloadPart
      .replace(/-/g, "+")
      .replace(/_/g, "/");

    const payload = JSON.parse(
      decodeURIComponent(
        atob(base64)
          .split("")
          .map((char) =>
            "%" + char.charCodeAt(0).toString(16).padStart(2, "0")
          )
          .join("")
      )
    );

    return payload.sub ? String(payload.sub) : null;
  } catch {
    return null;
  }
}

function setMessage(element, message, isError = false) {
  element.textContent = message;
  element.classList.toggle("error", isError);
  element.classList.toggle("success", Boolean(message) && !isError);
}

function showAuthMessage(message, isError = false) {
  setMessage($("#auth-message"), message, isError);
}

function showDashboardMessage(message, isError = false) {
  setMessage($("#dashboard-message"), message, isError);
}

function setButtonLoading(button, loading, loadingText = "Please wait...") {
  if (loading) {
    button.dataset.originalText = button.textContent.trim();
    button.textContent = loadingText;
    button.disabled = true;
  } else {
    button.textContent = button.dataset.originalText || "Submit";
    button.disabled = false;
  }
}

async function api(path, options = {}) {
  const headers = {
    ...(options.body ? { "Content-Type": "application/json" } : {}),
    ...(options.headers || {}),
  };

  if (options.auth && accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  const raw = await response.text();
  let data = {};

  try {
    data = raw ? JSON.parse(raw) : {};
  } catch {
    data = { detail: raw };
  }

  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map((item) => item.msg).join(", ")
      : data.detail || "Something went wrong.";

    throw new Error(detail);
  }

  return data;
}

function switchAuthTab(tab) {
  const isLogin = tab === "login";

  document.querySelectorAll("[data-auth-tab]").forEach((button) => {
    button.classList.toggle("active", button.dataset.authTab === tab);
  });

  $("#login-form").classList.toggle("hidden", !isLogin);
  $("#register-form").classList.toggle("hidden", isLogin);

  $("#auth-title").textContent = isLogin
    ? "Welcome back"
    : "Create your account";

  $("#auth-subtitle").textContent = isLogin
    ? "Sign in to continue to your workspace."
    : "Join InkSpace and start sharing your stories.";

  showAuthMessage("");
}

function showDashboard() {
  $("#auth-page").classList.add("hidden");
  $("#dashboard-page").classList.remove("hidden");

  const fallbackName = localStorage.getItem("blog_user_email") || "Writer";
  const displayName = currentUsername || fallbackName;

  $("#current-username").textContent = displayName;
  $("#user-avatar").textContent = displayName.charAt(0).toUpperCase();

  loadPosts();
}

function showAuthentication() {
  $("#dashboard-page").classList.add("hidden");
  $("#auth-page").classList.remove("hidden");
  switchAuthTab("login");
}

function saveTokens(data) {
  accessToken = data.access;
  refreshToken = data.refresh;
  currentUserId = getUserIdFromToken(accessToken);

  localStorage.setItem("blog_access", accessToken);
  localStorage.setItem("blog_refresh", refreshToken);
}

function clearSession() {
  accessToken = "";
  refreshToken = "";
  currentUserId = null;
  openCommentPosts.clear();

  localStorage.removeItem("blog_access");
  localStorage.removeItem("blog_refresh");
}

// AUTH TABS

document.querySelectorAll("[data-auth-tab]").forEach((button) => {
  button.addEventListener("click", () => {
    switchAuthTab(button.dataset.authTab);
  });
});

// REGISTER
// After registration, automatically try logging in with the new credentials.

$("#register-form").addEventListener("submit", async (event) => {
  event.preventDefault();

  const form = event.currentTarget;
  const button = form.querySelector('button[type="submit"]');
  const values = formObject(form);

  setButtonLoading(button, true, "Creating account...");
  showAuthMessage("");

  try {
    const registeredUser = await api("/api/register/", {
      method: "POST",
      body: JSON.stringify(values),
    });

    currentUsername = registeredUser.username || values.username;
    localStorage.setItem("blog_username", currentUsername);
    localStorage.setItem("blog_user_email", values.email.toLowerCase());

    // The registration endpoint returns user details, not JWT tokens.
    // Therefore, call the login endpoint after registration.
    try {
      const tokenData = await api("/api/token/", {
        method: "POST",
        body: JSON.stringify({
          email: values.email,
          password: values.password,
        }),
      });

      saveTokens(tokenData);
      form.reset();
      showDashboard();
      showDashboardMessage("Welcome to InkSpace! Your account is ready.");
    } catch {
      form.reset();
      switchAuthTab("login");
      $("#login-email").value = values.email;
      showAuthMessage(
        "Account created successfully! Please sign in to continue."
      );
    }
  } catch (error) {
    showAuthMessage(error.message, true);
  } finally {
    setButtonLoading(button, false);
  }
});

// LOGIN

$("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault();

  const form = event.currentTarget;
  const button = form.querySelector('button[type="submit"]');
  const values = formObject(form);
  const email = values.email.trim().toLowerCase();

  setButtonLoading(button, true, "Signing in...");
  showAuthMessage("");

  try {
    const data = await api("/api/token/", {
      method: "POST",
      body: JSON.stringify({
        email,
        password: values.password,
      }),
    });

    saveTokens(data);

    const savedEmail = (
      localStorage.getItem("blog_user_email") || ""
    ).toLowerCase();

    // Do not display another account's remembered username.
    if (savedEmail !== email) {
      currentUsername = "";
      localStorage.removeItem("blog_username");
    }

    localStorage.setItem("blog_user_email", email);

    form.reset();
    showDashboard();
    showDashboardMessage("You are signed in successfully.");
  } catch (error) {
    showAuthMessage(error.message, true);
  } finally {
    setButtonLoading(button, false);
  }
});

// LOGOUT

$("#logout-button").addEventListener("click", () => {
  clearSession();
  $("#post-form").reset();
  $("#posts").replaceChildren();
  showAuthentication();
  showAuthMessage("You have been logged out.");
});

// CREATE POST

$("#post-form").addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!accessToken) {
    showDashboardMessage("Please sign in before publishing.", true);
    showAuthentication();
    return;
  }

  const form = event.currentTarget;
  const button = form.querySelector('button[type="submit"]');

  setButtonLoading(button, true, "Publishing...");
  showDashboardMessage("");

  try {
    await api("/posts/", {
      method: "POST",
      auth: true,
      body: JSON.stringify(formObject(form)),
    });

    form.reset();
    currentFilter = "all";
    updateFilterButtons();
    await loadPosts();
    showDashboardMessage("Your post has been published!");
  } catch (error) {
    showDashboardMessage(error.message, true);
  } finally {
    setButtonLoading(button, false);
  }
});

// POST FILTERS

function updateFilterButtons() {
  document.querySelectorAll("[data-filter]").forEach((button) => {
    button.classList.toggle(
      "active",
      button.dataset.filter === currentFilter
    );
  });
}

document.querySelectorAll("[data-filter]").forEach((button) => {
  button.addEventListener("click", () => {
    currentFilter = button.dataset.filter;
    updateFilterButtons();
    loadPosts();
  });
});

$("#refresh-button").addEventListener("click", () => {
  loadPosts();
});

// SMALL DOM HELPERS

function makeElement(tag, className, text) {
  const element = document.createElement(tag);

  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;

  return element;
}

function formatDate(value) {
  if (!value) return "";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return "";

  return date.toLocaleString([], {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

// LOAD COMMENTS FOR ONE POST

async function loadComments(postId, section) {
  const list = section.querySelector(".comments-list");
  list.replaceChildren();

  try {
    const comments = await api(`/posts/${postId}/comments/`);

    if (!comments.length) {
      list.appendChild(
        makeElement("p", "no-comments", "No comments yet. Start the conversation!")
      );
      return;
    }

    comments.forEach((comment) => {
      const item = makeElement("article", "comment-item");
      const author = makeElement(
        "span",
        "comment-author",
        comment.author_username || "Anonymous"
      );
      const content = makeElement(
        "p",
        "comment-content",
        comment.content
      );

      item.append(author, content);

      if (comment.created_at) {
        item.appendChild(
          makeElement("div", "post-meta", formatDate(comment.created_at))
        );
      }

      list.appendChild(item);
    });
  } catch (error) {
    list.appendChild(
      makeElement("p", "no-comments", `Could not load comments: ${error.message}`)
    );
  }
}

function buildCommentsSection(post) {
  const section = makeElement("section", "comments-section");
  section.dataset.postId = String(post.id);

  const heading = makeElement("h4", "comments-heading", "Comments");
  const list = makeElement("div", "comments-list");

  const form = makeElement("form", "comment-form");
  const input = makeElement("input");
  input.name = "content";
  input.type = "text";
  input.maxLength = 5000;
  input.placeholder = "Write a comment...";
  input.setAttribute("aria-label", "Write a comment");
  input.required = true;

  const button = makeElement("button", "", "Send");
  button.type = "submit";

  form.append(input, button);
  section.append(heading, list, form);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!accessToken) {
      showDashboardMessage("Please sign in before commenting.", true);
      showAuthentication();
      return;
    }

    button.disabled = true;
    button.textContent = "Sending...";

    try {
      await api(`/posts/${post.id}/comments/`, {
        method: "POST",
        auth: true,
        body: JSON.stringify({ content: input.value.trim() }),
      });

      input.value = "";
      await loadComments(post.id, section);
      showDashboardMessage("Your comment has been added.");
    } catch (error) {
      showDashboardMessage(error.message, true);
    } finally {
      button.disabled = false;
      button.textContent = "Send";
    }
  });

  loadComments(post.id, section);

  return section;
}

// BUILD EACH POST CARD

function buildPostCard(post) {
  const card = makeElement("article", "post-card");

  const topLine = makeElement("div", "post-topline");
  const title = makeElement("h3", "", post.title);
  const isMine =
    currentUserId !== null &&
    String(post.author_id) === String(currentUserId);

  const badge = makeElement(
    "span",
    "post-badge",
    isMine ? "MY POST" : "BLOG POST"
  );

  topLine.append(title, badge);

  const metaText = [
    `By ${post.author_username || "Anonymous"}`,
    formatDate(post.created_at),
  ].filter(Boolean).join(" · ");

  const meta = makeElement("p", "post-meta", metaText);
  const content = makeElement("p", "post-content", post.content);

  const actions = makeElement("div", "post-actions");
  const commentButton = makeElement("button", "text-button", "View comments");
  commentButton.type = "button";

  const commentsSection = buildCommentsSection(post);
  commentsSection.classList.add("hidden");

  commentButton.addEventListener("click", async () => {
    const isOpen = !commentsSection.classList.contains("hidden");

    if (isOpen) {
      commentsSection.classList.add("hidden");
      openCommentPosts.delete(post.id);
      commentButton.textContent = "View comments";
    } else {
      commentsSection.classList.remove("hidden");
      openCommentPosts.add(post.id);
      commentButton.textContent = "Hide comments";
      await loadComments(post.id, commentsSection);
    }
  });

  actions.appendChild(commentButton);
  card.append(topLine, meta, content, actions, commentsSection);

  if (openCommentPosts.has(post.id)) {
    commentsSection.classList.remove("hidden");
    commentButton.textContent = "Hide comments";
  }

  return card;
}

// LOAD ALL POSTS OR ONLY THE CURRENT USER'S POSTS

async function loadPosts() {
  const container = $("#posts");
  container.replaceChildren();

  container.appendChild(
    makeElement("div", "loading-state", "Loading posts...")
  );

  try {
    const posts = await api("/posts/");
    container.replaceChildren();

    const visiblePosts =
      currentFilter === "mine"
        ? posts.filter(
            (post) =>
              currentUserId !== null &&
              String(post.author_id) === String(currentUserId)
          )
        : posts;

    if (!visiblePosts.length) {
      const message =
        currentFilter === "mine"
          ? "You haven't published any posts yet. Create your first story!"
          : "No posts yet. Be the first to share a story!";

      container.appendChild(makeElement("div", "empty-state", message));
      return;
    }

    visiblePosts.forEach((post) => {
      container.appendChild(buildPostCard(post));
    });
  } catch (error) {
    container.replaceChildren();

    container.appendChild(
      makeElement(
        "div",
        "empty-state",
        `Could not load posts: ${error.message}`
      )
    );
  }
}

// INITIAL PAGE

updateFilterButtons();

if (accessToken) {
  showDashboard();
} else {
  showAuthentication();
}