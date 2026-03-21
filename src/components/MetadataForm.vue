<script setup lang="ts">
import { useMetadataStore } from "@/stores/metadata";

const meta = useMetadataStore();
</script>

<template>
  <section class="metadata-form">
    <h3>Book Metadata</h3>

    <div class="field">
      <label for="meta-title">Title <span class="required">*</span></label>
      <input
        id="meta-title"
        type="text"
        :value="meta.title"
        placeholder="e.g. The Great Gatsby"
        @input="meta.setTitle(($event.target as HTMLInputElement).value)"
      />
    </div>

    <div class="field">
      <label for="meta-author">Author <span class="required">*</span></label>
      <input
        id="meta-author"
        type="text"
        :value="meta.author"
        placeholder="e.g. F. Scott Fitzgerald"
        @input="meta.setAuthor(($event.target as HTMLInputElement).value)"
      />
    </div>

    <div class="field">
      <label for="meta-language">Language</label>
      <input
        id="meta-language"
        type="text"
        :value="meta.language"
        placeholder="e.g. en"
        maxlength="10"
        @input="meta.setLanguage(($event.target as HTMLInputElement).value)"
      />
    </div>

    <div class="field">
      <label for="meta-publisher">Publisher</label>
      <input
        id="meta-publisher"
        type="text"
        :value="meta.publisher"
        placeholder="Optional"
        @input="meta.setPublisher(($event.target as HTMLInputElement).value)"
      />
    </div>

    <div class="field">
      <label for="meta-isbn">ISBN</label>
      <input
        id="meta-isbn"
        type="text"
        :value="meta.isbn"
        placeholder="Optional"
        @input="meta.setIsbn(($event.target as HTMLInputElement).value)"
      />
    </div>

    <div class="field">
      <label for="meta-description">Description</label>
      <textarea
        id="meta-description"
        :value="meta.description"
        placeholder="Optional synopsis or description"
        rows="3"
        @input="meta.setDescription(($event.target as HTMLTextAreaElement).value)"
      />
    </div>
  </section>
</template>

<style scoped>
.metadata-form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.metadata-form h3 {
  margin: 0 0 0.25rem;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--color-heading, #ccc);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

label {
  font-size: 0.8rem;
  color: var(--color-text-muted, #aaa);
}

.required {
  color: #f87171;
}

input,
textarea {
  background: var(--color-background-soft, #1e1e1e);
  color: var(--color-text, #eee);
  border: 1px solid var(--color-border, #444);
  border-radius: 4px;
  padding: 0.35rem 0.55rem;
  font-size: 0.85rem;
  outline: none;
  resize: vertical;
}

input:focus,
textarea:focus {
  border-color: var(--color-brand, #4f8cff);
}
</style>
