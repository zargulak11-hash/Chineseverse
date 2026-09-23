// Shared Framer Motion variants/transitions — one small vocabulary reused
// across pages instead of bespoke spring configs scattered per component.
export const spring = { type: "spring", stiffness: 340, damping: 28, mass: 0.9 };
export const softSpring = { type: "spring", stiffness: 220, damping: 24 };
export const snapSpring = { type: "spring", stiffness: 420, damping: 22 };

export const pageVariants = {
  initial: { opacity: 0, y: 14 },
  animate: { opacity: 1, y: 0, transition: { ...softSpring, delay: 0.05 } },
  exit: { opacity: 0, y: -8, transition: { duration: 0.15, ease: "easeIn" } },
};

export const staggerContainer = {
  animate: { transition: { staggerChildren: 0.06, delayChildren: 0.04 } },
};

export const staggerItem = {
  initial: { opacity: 0, y: 18, scale: 0.98 },
  animate: { opacity: 1, y: 0, scale: 1, transition: spring },
};

export const popIn = {
  initial: { opacity: 0, scale: 0.85 },
  animate: { opacity: 1, scale: 1, transition: snapSpring },
  exit: { opacity: 0, scale: 0.9, transition: { duration: 0.15 } },
};

export const tapScale = { scale: 0.96 };
export const hoverLift = { y: -2, transition: spring };
