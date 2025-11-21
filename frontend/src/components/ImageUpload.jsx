/* eslint-disable react/prop-types */
const ACCEPTED_TYPES = ["image/png", "image/jpeg", "image/jpg"];

function ImageUpload({ objectKey, label, file, preview, onFileSelect }) {
  const inputId = `image-upload-${objectKey}-input`;

  const handleFileChange = (event) => {
    const selected = event.target.files?.[0];
    if (!selected) return;
    if (!ACCEPTED_TYPES.includes(selected.type)) {
      alert("Please upload a PNG or JPEG image.");
      return;
    }
    onFileSelect(objectKey, selected);
  };

  return (
    <div
      id={`image-upload-${objectKey}`}
      className="rounded-2xl border border-white/10 bg-white/5 p-4 shadow-lg backdrop-blur"
    >
      <div
        id={`image-upload-${objectKey}-dropzone`}
        className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-white/30 p-6 text-center hover:border-brand-500"
      >
        <p className="text-sm text-white/80">{label}</p>
        <p className="mt-2 text-xs text-white/60">
          {file ? file.name : "Drop image here or click to browse"}
        </p>
        <input
          id={inputId}
          type="file"
          accept="image/png,image/jpeg"
          className="mt-4 block text-sm text-white"
          onChange={handleFileChange}
        />
      </div>

      {preview && (
        <div
          id={`image-upload-${objectKey}-preview`}
          className="mt-4 overflow-hidden rounded-lg border border-white/20"
        >
          <img
            src={preview}
            alt={`${objectKey} preview`}
            className="h-48 w-full object-cover"
          />
        </div>
      )}
    </div>
  );
}

export default ImageUpload;

