import i18n from "./i18n.js";

// The API's `detail` strings are English (they are also what logs and tests
// read), and api.js used to show them verbatim -- so a Russian, Tajik or
// Chinese learner got "Invalid username or password" or "This location isn't
// unlocked yet" in English. The learner-facing ones are mapped to apiErrors.*
// here; anything unmapped (admin tools, rare internals) keeps the server text.
const EXACT = {
  "Invalid username or password": "invalidLogin",
  "username already registered": "usernameTaken",
  "username already taken": "usernameTaken",
  "email already registered": "emailTaken",
  "This account has been deactivated": "deactivated",
  "This email is linked to a different Google account": "googleOtherAccount",
  "Google account has no verified email": "googleNoEmail",
  "Not authenticated": "sessionExpired",
  "Invalid or expired token": "sessionExpired",
  "This location isn't unlocked yet": "locationLocked",
  "This lesson is locked. Complete the previous lesson first.": "lessonLocked",
  "This case is above your current HSK level": "caseAboveLevel",
  "Quest not completed yet": "questNotDone",
  "Quest already claimed": "questClaimed",
  "Only JPG, PNG or WEBP images are allowed": "imageType",
  "Image must be 3 MB or smaller": "imageSize",
  "You cannot follow yourself": "followSelf",
  "No Pet Teacher content available yet": "petNoContent",
  "This lesson has no linked vocabulary or grammar to practice yet": "lessonNoPractice",
  "Not enough content at this level to build a practice round": "notEnoughContent",
  "This practice round is already finished": "roundFinished",
  "This question was already answered": "alreadyAnswered",
  "Answer at least one question before finishing": "answerOne",
  "The placement test is part of onboarding, which is already complete": "placementDone",
  "Lessons are completed by passing their practice round": "lessonByPractice",
  "No stroke data available for this character": "noStrokeData",
};

export function localizeApiError(detail, status) {
  if (typeof detail === "string") {
    const key = EXACT[detail];
    if (key) return i18n.t(`apiErrors.${key}`);
    const mission = /^This mission opens at HSK (\d+)$/.exec(detail);
    if (mission) return i18n.t("apiErrors.missionLocked", { level: mission[1] });
    if (status === 404 && / not found$/i.test(detail)) return i18n.t("apiErrors.notFound");
    return detail;
  }
  // FastAPI's 422 validation body is a list, not a sentence.
  if (status === 422) return i18n.t("apiErrors.invalidInput");
  if (status >= 500) return i18n.t("apiErrors.server");
  return i18n.t("apiErrors.requestFailed", { status });
}
