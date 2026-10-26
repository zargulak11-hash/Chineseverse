import i18n from "./i18n.js";

// The API's `detail` strings are English (they are also what logs and tests
// read), and api.js used to show them verbatim -- so a Russian, Tajik or
// Chinese learner got "Invalid username or password" or "This location isn't
// unlocked yet" in English. The learner-facing ones are mapped to apiErrors.*
// here; anything unmapped (admin tools, rare internals) keeps the server text.
// 422 fields that have their own message (apiErrors.invalidField.*).
const FIELD_ERRORS = ["email", "username", "password"];

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
  // 501 when the server has no GOOGLE_CLIENT_ID (its text is for the operator)
  "Google Sign-In is not configured on this server. Set GOOGLE_CLIENT_ID in backend/.env and restart the API.": "googleServerOff",
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
  // routers/me.py change_password
  "Current password is incorrect": "currentPasswordWrong",
  "Enter your current password": "currentPasswordMissing",
  "The new password must be at least 6 characters": "passwordTooShort",
  "The new password must be at most 128 characters": "passwordTooLong",
  "The new passwords don't match": "newPasswordMismatch",
  "The new password must be different from the current one": "passwordSame",
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
  // Sentences a learner meets in normal use that were still English
  // everywhere (found by listing every detail the API can return).
  // services/sentence.py (One Sentence)
  "Enter a Chinese sentence (at least two characters)": "sentenceInput",
  "No HSK words were found in this sentence": "sentenceNoWords",
  "This sentence is too short to build a lesson from": "sentenceTooShort",
  "The sentence should be written in Chinese characters": "sentenceNotChinese",
  // stories, vocabulary, Character DNA
  "Select some Chinese text": "selectChinese",
  "This word is already in your review": "alreadyInReview",
  "This word can't be practised here": "wordNotPractisable",
  "This character isn't in the ChineseVerse curriculum yet": "charNotInCurriculum",
  "Give one Chinese character": "giveOneChar",
  "This chapter has nothing to practise yet": "chapterNothing",
  "No words to practise at this level": "noWordsAtLevel",
  "Not enough curriculum words to build this case yet": "caseNotReady",
  "Not enough curriculum words to build this place yet": "placeNotReady",
  "This item no longer exists": "itemGone",
  // practice rounds (services/practice.py)
  "Answer the question first": "answerFirst",
  "Answer the question before saying it aloud": "answerBeforeSpeaking",
  "You've already practised saying this one": "alreadySpoken",
  "This question has nothing to say aloud": "nothingToSay",
  "This answer was right -- there is nothing to explain": "nothingToExplain",
  "This kind of question can't be explained here": "cantExplain",
  "Type your answer for this question": "typeAnswer",
  // roleplay, tone coach, sound world, exam
  "Write something to say": "writeSomething",
  "Say something before finishing": "saySomething",
  "This conversation is complete -- finish it to see your summary": "conversationComplete",
  "This conversation is finished": "conversationFinished",
  "The recording should be between a moment and 5 seconds long": "recordingLength",
  "This speed isn't unlocked yet": "speedLocked",
  "This exam attempt is over": "examOver",
  "An exam attempt is already in progress": "examInProgress",
  "This exam is not open: finish the level's lessons first": "examNotOpen",
  // When the AI is down or past its budget (services/roleplay.py,
  // practice.explain_answer): shown exactly when the AI fails, and they
  // were the only learner-facing answers left in English.
  "AI conversations are not available on this server right now": "aiRoleplayOff",
  "AI conversations are not available right now. Try again later.": "aiRoleplayLater",
  "Your conversation partner didn't answer. Send your message again in a moment.": "aiPartnerSilent",
  "AI explanations are not available right now": "aiExplainOff",
  "The explanation couldn't be written right now. Try again in a moment.": "aiExplainFailed",
  // services/password_reset.py, routers/auth.py (forgot password, set a password with Google)
  "Password reset by email isn't available right now": "resetUnavailable",
  "This reset link is invalid or was already used": "resetInvalid",
  "This reset link has expired": "resetExpired",
  "Your account isn't linked to a Google account": "googleNotLinked",
  "This Google account isn't the one linked to your ChineseVerse account": "googleWrongAccount",
  "Please confirm with Google again": "googleConfirmAgain",
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
  // FastAPI's 422 validation body is a list, not a sentence. For the fields
  // a learner types by hand (sign-up, settings) name the field and its rule:
  // "some of the data isn't valid" left a mistyped email with no next step.
  if (status === 422) {
    const field = Array.isArray(detail) ? detail.map((d) => d?.loc?.[d.loc.length - 1]).find((f) => FIELD_ERRORS.includes(f)) : null;
    return field ? i18n.t(`apiErrors.invalidField.${field}`) : i18n.t("apiErrors.invalidInput");
  }
  if (status >= 500) return i18n.t("apiErrors.server");
  return i18n.t("apiErrors.requestFailed", { status });
}
