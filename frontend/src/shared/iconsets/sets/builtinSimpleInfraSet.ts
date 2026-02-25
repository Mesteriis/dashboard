import * as simpleIcons from "simple-icons";
import {
  isInfraIcon,
  isSimpleIconLike,
  simpleToOption,
  type BuiltinIconPickerSet,
} from "@/shared/iconsets/simpleIconsUtils";

const INFRA_OPTIONS = Object.values(simpleIcons)
  .filter(isSimpleIconLike)
  .filter((icon) => isInfraIcon(icon))
  .sort((left, right) => left.title.localeCompare(right.title))
  .map((icon) => simpleToOption(icon, "simple-infra"));

export const BUILTIN_ICON_SET: BuiltinIconPickerSet = {
  id: "builtin:simple-infra",
  label: "Infrastructure",
  options: INFRA_OPTIONS,
};
