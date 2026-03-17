"""Generate test fixture images for KindleOCR tests."""

from PIL import Image, ImageDraw
import os


def main():
    fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "test-fixtures")
    os.makedirs(fixtures_dir, exist_ok=True)

    # 1. Simple page with text
    img = Image.new("RGB", (800, 1200), "white")
    draw = ImageDraw.Draw(img)
    draw.text(
        (100, 100),
        "Chapter 1\n\nThis is a sample page of text for OCR testing.\n"
        "It contains multiple lines that should be recognized.",
        fill="black",
    )
    img.save(os.path.join(fixtures_dir, "sample-page-01.png"))

    # 2. Second page (different content)
    img2 = Image.new("RGB", (800, 1200), "white")
    draw2 = ImageDraw.Draw(img2)
    draw2.text(
        (100, 100),
        "This is the second page of the sample book.\n"
        "It has different content from the first page.",
        fill="black",
    )
    img2.save(os.path.join(fixtures_dir, "sample-page-02.png"))

    # 3. Duplicate of page 1 (for duplicate detection)
    img.save(os.path.join(fixtures_dir, "sample-page-01-duplicate.png"))

    # 4. Blank page (edge case)
    blank = Image.new("RGB", (800, 1200), "white")
    blank.save(os.path.join(fixtures_dir, "blank-page.png"))

    # 5. Noisy/low-quality page
    noisy = Image.new("L", (800, 1200), 200)
    draw_n = ImageDraw.Draw(noisy)
    draw_n.text((100, 100), "Noisy page with low contrast text", fill=160)
    noisy.save(os.path.join(fixtures_dir, "noisy-page.png"))

    # 6. Cover image
    cover = Image.new("RGB", (600, 900), (40, 60, 120))
    draw_c = ImageDraw.Draw(cover)
    draw_c.text((150, 350), "SAMPLE BOOK", fill="white")
    draw_c.text((200, 420), "Test Author", fill=(200, 200, 200))
    cover.save(os.path.join(fixtures_dir, "cover.jpg"), "JPEG")

    print(f"Created 6 test fixture images in {fixtures_dir}")


if __name__ == "__main__":
    main()
