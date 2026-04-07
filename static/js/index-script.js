// FH TechStore — Index Page Scripts

// === Carousel ===
let slideIndex = 1;
let autoSlideInterval;

function showSlide(n) {
    const slides = document.querySelectorAll('.carousel-slide');
    const indicators = document.querySelectorAll('.carousel-indicator');

    if (!slides.length) return;

    if (n > slides.length) slideIndex = 1;
    if (n < 1) slideIndex = slides.length;

    slides.forEach(slide => {
        slide.classList.remove('active');
    });

    indicators.forEach(indicator => {
        indicator.classList.remove('active');
    });

    slides[slideIndex - 1].classList.add('active');
    if (indicators[slideIndex - 1]) {
        indicators[slideIndex - 1].classList.add('active');
    }
}

function nextSlide() {
    showSlide(++slideIndex);
    resetAutoSlide();
}

function prevSlide() {
    showSlide(--slideIndex);
    resetAutoSlide();
}

function currentSlide(n) {
    slideIndex = n;
    showSlide(slideIndex);
    resetAutoSlide();
}

function startAutoSlide() {
    autoSlideInterval = setInterval(function () {
        nextSlide();
    }, 4000);
}

function resetAutoSlide() {
    clearInterval(autoSlideInterval);
    startAutoSlide();
}

// === Smooth Scroll ===
function smoothScrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

// === Fade-in Animation ===
function handleFadeIn() {
    const fadeEls = document.querySelectorAll('.fade-in');
    const observer = new IntersectionObserver(function (entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, { threshold: 0.1 });

    fadeEls.forEach(el => observer.observe(el));
}

// === Init ===
document.addEventListener('DOMContentLoaded', function () {
    showSlide(slideIndex);
    startAutoSlide();
    handleFadeIn();
});
