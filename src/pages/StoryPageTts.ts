export type TtsStatus = "idle" | "playing" | "paused";

export interface StoryPageTtsState {
  activeSentenceIndex: number;
  sentenceCount: number;
  status: TtsStatus;
  isSupported: boolean;
}

const splitIntoSentenceChunks = (text: string): string[] => {
  if (typeof Intl !== "undefined" && "Segmenter" in Intl) {
    const segmenter = new Intl.Segmenter(undefined, { granularity: "sentence" });
    const chunks = Array.from(segmenter.segment(text), (segment) => segment.segment);
    if (chunks.length > 0) {
      return chunks;
    }
  }

  const fallbackChunks = text.match(/[^.!?]+(?:[.!?]+|$)/g);
  return fallbackChunks ?? [text];
};

export function injectSentenceMarkers(html: string): { html: string; sentences: string[] } {
  const template = document.createElement("template");
  template.innerHTML = html;

  const walker = document.createTreeWalker(template.content, NodeFilter.SHOW_TEXT);
  const textNodes: Text[] = [];

  let currentNode = walker.nextNode();
  while (currentNode) {
    if (currentNode.nodeType === Node.TEXT_NODE) {
      textNodes.push(currentNode as Text);
    }
    currentNode = walker.nextNode();
  }

  let sentenceIndex = 0;
  const sentences: string[] = [];

  for (const textNode of textNodes) {
    const text = textNode.textContent ?? "";
    if (!text.trim()) {
      continue;
    }

    const chunks = splitIntoSentenceChunks(text);
    if (chunks.length === 0) {
      continue;
    }

    const fragment = document.createDocumentFragment();
    let hasWrappedSentence = false;

    for (const chunk of chunks) {
      if (!chunk) {
        continue;
      }

      if (!chunk.trim()) {
        fragment.append(document.createTextNode(chunk));
        continue;
      }

      const sentenceSpan = document.createElement("span");
      sentenceSpan.className = "tts-sentence";
      sentenceSpan.dataset.ttsIndex = String(sentenceIndex);
      sentenceSpan.tabIndex = 0;
      sentenceSpan.textContent = chunk;
      fragment.append(sentenceSpan);

      sentences.push(chunk.replace(/\s+/g, " ").trim());
      sentenceIndex += 1;
      hasWrappedSentence = true;
    }

    if (hasWrappedSentence) {
      textNode.parentNode?.replaceChild(fragment, textNode);
    }
  }

  return {
    html: template.innerHTML,
    sentences
  };
}

export function createStoryPageTtsController(onChange: (state: StoryPageTtsState) => void) {
  const isSupported =
    typeof window !== "undefined" &&
    "speechSynthesis" in window &&
    "SpeechSynthesisUtterance" in window;

  let readerContentElement: HTMLDivElement | null = null;
  let activeSentenceIndex = -1;
  let sentenceCount = 0;
  let status: TtsStatus = "idle";
  let sentences: string[] = [];
  let currentUtterance: SpeechSynthesisUtterance | null = null;

  const emit = () => {
    onChange({
      activeSentenceIndex,
      sentenceCount,
      status,
      isSupported
    });
    syncHighlight();
  };

  const syncHighlight = () => {
    if (!readerContentElement) {
      return;
    }

    const highlighted = readerContentElement.querySelectorAll(".tts-sentence.is-active");
    highlighted.forEach((element) => element.classList.remove("is-active"));

    if (activeSentenceIndex < 0) {
      return;
    }

    const activeElement = readerContentElement.querySelector(
      `.tts-sentence[data-tts-index="${activeSentenceIndex}"]`
    );

    if (activeElement instanceof HTMLElement) {
      activeElement.classList.add("is-active");
      activeElement.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  };

  const stop = () => {
    if (isSupported) {
      window.speechSynthesis.cancel();
    }

    currentUtterance = null;
    status = "idle";
    activeSentenceIndex = -1;
    emit();
  };

  const speakFromSentence = (index: number) => {
    if (!isSupported || !sentences.length || index >= sentences.length) {
      stop();
      return;
    }

    const utterance = new SpeechSynthesisUtterance(sentences[index]);
    currentUtterance = utterance;
    activeSentenceIndex = index;
    status = "playing";
    utterance.onstart = () => {
      activeSentenceIndex = index;
      status = "playing";
      emit();
    };
    utterance.onend = () => {
      if (currentUtterance !== utterance) {
        return;
      }
      speakFromSentence(index + 1);
    };
    utterance.onerror = () => {
      if (currentUtterance !== utterance) {
        return;
      }
      speakFromSentence(index + 1);
    };
    emit();
    window.speechSynthesis.speak(utterance);
  };

  return {
    bindReader(element: HTMLDivElement | null) {
      readerContentElement = element;
      syncHighlight();
    },
    prepareChapter(html: string) {
      const marked = injectSentenceMarkers(html);
      sentences = marked.sentences;
      sentenceCount = sentences.length;
      stop();
      emit();
      return marked;
    },
    play() {
      if (!isSupported || !sentences.length) {
        return;
      }

      if (status === "paused") {
        window.speechSynthesis.resume();
        status = "playing";
        emit();
        return;
      }

      window.speechSynthesis.cancel();
      const startIndex = activeSentenceIndex >= 0 ? activeSentenceIndex : 0;
      speakFromSentence(startIndex);
    },
    pause() {
      if (!isSupported || status !== "playing") {
        return;
      }

      window.speechSynthesis.pause();
      status = "paused";
      emit();
    },
    stop,
    activateFromTarget(target: EventTarget | null) {
      if (!isSupported) {
        return;
      }

      const element = target as HTMLElement | null;
      const sentenceElement = element?.closest(".tts-sentence");
      if (!(sentenceElement instanceof HTMLElement)) {
        return;
      }

      const sentenceIndex = Number(sentenceElement.dataset.ttsIndex);
      if (Number.isNaN(sentenceIndex)) {
        return;
      }

      window.speechSynthesis.cancel();
      speakFromSentence(sentenceIndex);
    },
    syncHighlight,
    destroy() {
      stop();
      readerContentElement = null;
    }
  };
}
