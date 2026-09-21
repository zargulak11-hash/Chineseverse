const FACES = {
  fox: "🦊",
  wolf: "🐺",
  snake: "🐍",
  cheetah: "🐆",
  cat: "🐱",
  dog: "🐶",
  tiger: "🐯",
  rabbit: "🐰",
  bird: "🐦",
  capybara: "🦫",
  panther: "🐈‍⬛",
  sheep: "🐑",
  panda: "🐼",
  "red-panda": "🦝",
  phoenix: "🐦‍🔥",
  "golden-dragon": "🐉",
};

const FALLBACK = "🐾";

export function animalFace(slug) {
  return FACES[slug] || FALLBACK;
}