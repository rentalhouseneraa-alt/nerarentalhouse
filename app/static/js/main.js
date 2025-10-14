/* ===========================
   Main JS (main.js)
   =========================== */

// Fade-in animation on scroll
document.addEventListener("DOMContentLoaded", () => {
  const fadeElems = document.querySelectorAll(".fade-in");

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = 1;
        entry.target.style.transform = "translateY(0)";
      }
    });
  }, { threshold: 0.2 });

  fadeElems.forEach(el => {
    el.style.opacity = 0;
    el.style.transform = "translateY(20px)";
    el.style.transition = "all 0.8s ease";
    observer.observe(el);
  });
});

// Smooth back-to-top button
window.addEventListener("scroll", () => {
  const topBtn = document.querySelector("#backToTop");
  if (!topBtn) return;

  if (window.scrollY > 200) {
    topBtn.classList.add("show");
  } else {
    topBtn.classList.remove("show");
  }
});

function scrollToTop() {
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// Add ripple effect to buttons
document.querySelectorAll(".btn").forEach(btn => {
  btn.addEventListener("click", function(e) {
    const circle = document.createElement("span");
    const diameter = Math.max(this.clientWidth, this.clientHeight);
    const radius = diameter / 2;

    circle.style.width = circle.style.height = `${diameter}px`;
    circle.style.left = `${e.clientX - this.offsetLeft - radius}px`;
    circle.style.top = `${e.clientY - this.offsetTop - radius}px`;
    circle.classList.add("ripple");

    const ripple = this.getElementsByClassName("ripple")[0];
    if (ripple) {
      ripple.remove();
    }

    this.appendChild(circle);
  });
});

// Create ripple effect CSS dynamically
const style = document.createElement("style");
style.innerHTML = `
  .ripple {
    position: absolute;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.6);
    animation: ripple 0.6s linear;
    transform: scale(0);
    pointer-events: none;
  }
  @keyframes ripple {
    to {
      transform: scale(4);
      opacity: 0;
    }
  }
  .btn {
    position: relative;
    overflow: hidden;
  }
  #backToTop {
    position: fixed;
    bottom: 25px;
    right: 25px;
    background: #0d6efd;
    color: #fff;
    border: none;
    border-radius: 50%;
    width: 44px;
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    opacity: 0;
    visibility: hidden;
    transition: all 0.4s ease;
    z-index: 999;
  }
  #backToTop.show {
    opacity: 1;
    visibility: visible;
  }
`;
document.head.appendChild(style);
