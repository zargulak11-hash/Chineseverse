import i18n from "./i18n.js";

// The API's `detail` strings are English (they are also what logs and tests
// read), and api.js used to show them verbatim -- so a Russian, Tajik or
// Chinese learner got "Invalid username or password" or "This location isn't
// unlocked yet" in English. The learner-facing ones are mapped to apiErrors.*
// here; anything unmapped (admin tools, rare internals) keeps the server text.
const EXACT = {
  "Invalid username or password": "invalidLogin",
  // services/login_throttle.py (429 after repeated failed sign-ins)
  "Too many sign-in attempts. Please wait a few minutes and try again.": "loginLocked",
  "username already registered": "usernameTaken",
  "username already taken": "usernameTaken",
  "email already registered": "emailTaken",
  "This account has been deactivated": "deactivated",
  "This email is linked to a different Google account": "googleOtherAccount",
  "Google account has no verified email": "googleNoEmail",
  "Google sign-in could not be verified": "googleInvalid",
  "Google credential has no account id": "googleInvalid",
  "Could not reach Google to verify the sign-in": "googleUnreachable",
  // routers/auth.py POST /auth/github/session (ticket missing or used)
  "This GitHub sign-in has expired. Please try again.": "githubExpired",
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
  "Placement attempt already finished": "placementDone", // a double submit
  // routers/onboarding.py: finishing placement before the earlier steps are saved
  "Choose your companion before finishing onboarding": "onboardingCompanionFirst",
  "Answer the onboarding questions before finishing onboarding": "onboardingQuestionsFirst",
  "Lessons are completed by passing their practice round": "lessonByPractice",
  "No stroke data available for this character": "noStrokeData",
  "This tracing attempt was already used": "traceUsed",
  "This tracing attempt has expired": "traceExpired",
  // services/grammar_lesson.py
  "A full explanation isn't available right now — the examples below still work": "lessonUnavailable",
  "You've asked for many new explanations this hour — try again a bit later": "aiLimit",
  "Write the sentence in Chinese characters": "writeChinese",
  "This grammar point has no example to practice at this level": "grammarNoExample",
  // routers/assistant.py
  "You've sent a lot of messages this hour — take a short break and try again": "chatLimit",
};

// routers/assistant.py: "<file name>: <problem>" -- the name stays, the
// problem is translated.
const FILE_ERRORS = [
  [": the file is too large", "fileTooLarge"],
  [": the file could not be read", "fileRead"],
  [": the file is not a valid", "fileInvalid"],
  [": this file type isn't supported", "fileType"],
  [": text files must be UTF-8", "fileUtf8"],
];

export function localizeApiError(detail, status) {
  if (typeof detail === "string") {
    const key = EXACT[detail];
    if (key) return i18n.t(`apiErrors.${key}`);
    if (detail.startsWith("Trace not accepted")) return i18n.t("apiErrors.traceRejected");
    for (const [marker, fileKey] of FILE_ERRORS) {
      const at = detail.indexOf(marker);
      if (at > 0) return i18n.t(`apiErrors.${fileKey}`, { name: detail.slice(0, at) });
    }
    const mission = /^This mission opens at HSK (\d+)$/.exec(detail);
    if (mission) return i18n.t("apiErrors.missionLocked", { level: mission[1] });
    // services/world_map.scene_gate: a place above the learner's HSK level.
    const place = /^This place opens at HSK (\d+)$/.exec(detail);
    if (place) return i18n.t("apiErrors.placeLocked", { level: place[1] });
    // services/stories.view: a story above the learner's HSK level.
    const story = /^This story opens at HSK (\d+)$/.exec(detail);
    if (story) return i18n.t("apiErrors.storyLocked", { level: story[1] });
    if (status === 404 && / not found$/i.test(detail)) return i18n.t("apiErrors.notFound");
    return detail;
  }
  // FastAPI's 422 validation body is a list, not a sentence.
  if (status === 422) return i18n.t("apiErrors.invalidInput");
  if (status >= 500) return i18n.t("apiErrors.server");
  return i18n.t("apiErrors.requestFailed", { status });
}
