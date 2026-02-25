import * as simpleIcons from "simple-icons";
import {
  isInfraIcon,
  isSimpleIconLike,
  simpleToOption,
  type BuiltinIconPickerSet,
} from "@/shared/iconsets/simpleIconsUtils";

const SERVICE_OPTIONS = Object.values(simpleIcons)
  .filter(isSimpleIconLike)
  .filter((icon) => !isInfraIcon(icon))
  .sort((left, right) => left.title.localeCompare(right.title))
  .map((icon) => simpleToOption(icon, "simple-services"));

export const BUILTIN_ICON_SET: BuiltinIconPickerSet = {
  id: "builtin:simple-services",
  label: "Services",
  options: SERVICE_OPTIONS,
};
