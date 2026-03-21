import { defineStore } from "pinia";
import { ref } from "vue";

export const useMetadataStore = defineStore("metadata", () => {
  const title = ref("");
  const author = ref("");
  const language = ref("en");
  const description = ref("");
  const publisher = ref("");
  const isbn = ref("");
  const coverImagePath = ref("");

  function setTitle(value: string) { title.value = value; }
  function setAuthor(value: string) { author.value = value; }
  function setLanguage(value: string) { language.value = value; }
  function setDescription(value: string) { description.value = value; }
  function setPublisher(value: string) { publisher.value = value; }
  function setIsbn(value: string) { isbn.value = value; }
  function setCoverImagePath(value: string) { coverImagePath.value = value; }

  function reset() {
    title.value = "";
    author.value = "";
    language.value = "en";
    description.value = "";
    publisher.value = "";
    isbn.value = "";
    coverImagePath.value = "";
  }

  return {
    title,
    author,
    language,
    description,
    publisher,
    isbn,
    coverImagePath,
    setTitle,
    setAuthor,
    setLanguage,
    setDescription,
    setPublisher,
    setIsbn,
    setCoverImagePath,
    reset,
  };
});
