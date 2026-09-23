(function () {
  "use strict";

  // Header scroll state
  const header = document.querySelector(".header");
  function onScroll() {
    if (header) {
      header.classList.toggle("header--scrolled", window.scrollY > 20);
    }
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  // Mobile menu
  const toggle = document.querySelector(".nav__toggle");
  const navLinks = document.querySelector(".nav__links");
  if (toggle && navLinks) {
    toggle.addEventListener("click", () => {
      const open = toggle.classList.toggle("nav__toggle--open");
      navLinks.classList.toggle("nav__links--open", open);
      toggle.setAttribute("aria-expanded", String(open));
    });

    navLinks.querySelectorAll("a").forEach((link) =>
      link.addEventListener("click", () => {
        toggle.classList.remove("nav__toggle--open");
        navLinks.classList.remove("nav__links--open");
        toggle.setAttribute("aria-expanded", "false");
      })
    );
  }

  // Scroll reveal observer
  const reveals = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.1, rootMargin: "0px 0px -40px 0px" }
    );
    reveals.forEach((el) => observer.observe(el));
  } else {
    reveals.forEach((el) => el.classList.add("visible"));
  }

  // Copy to clipboard
  document.querySelectorAll(".copy-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const text = btn.dataset.copy;
      if (!text) return;

      try {
        await navigator.clipboard.writeText(text);
        const original = btn.textContent;
        btn.textContent = "Copied!";
        btn.classList.add("copied");
        setTimeout(() => {
          btn.textContent = original;
          btn.classList.remove("copied");
        }, 2000);
      } catch (err) {
        btn.textContent = "Error";
        setTimeout(() => {
          btn.textContent = "Copy";
        }, 2000);
      }
    });
  });

  // Interactive Demo Explorer Tabs
  const demoTabs = document.querySelectorAll(".demo-tab");
  const demoContents = document.querySelectorAll(".demo-content");

  demoTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const targetId = tab.dataset.tab;
      if (!targetId) return;

      demoTabs.forEach((t) => t.classList.remove("active"));
      demoContents.forEach((c) => c.classList.remove("active"));

      tab.classList.add("active");
      const targetContent = document.getElementById(targetId);
      if (targetContent) {
        targetContent.classList.add("active");
      }
    });
  });

  // Code Switcher Tabs (CLI vs Python vs CI/CD)
  const codeBtns = document.querySelectorAll(".code-switcher__btn");
  const codeSnippets = document.querySelectorAll(".code-snippet");

  codeBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetSnippetId = btn.dataset.snippet;
      if (!targetSnippetId) return;

      codeBtns.forEach((b) => b.classList.remove("active"));
      codeSnippets.forEach((s) => s.classList.remove("active"));

      btn.classList.add("active");
      const targetSnippet = document.getElementById(targetSnippetId);
      if (targetSnippet) {
        targetSnippet.classList.add("active");
      }
    });
  });
})();

