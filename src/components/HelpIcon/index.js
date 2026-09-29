import {
  ArrowPathIcon,
  ArrowRightIcon,
  BellAlertIcon,
  BriefcaseIcon,
  ChartBarIcon,
  ChatBubbleLeftRightIcon,
  CheckCircleIcon,
  ComputerDesktopIcon,
  CreditCardIcon,
  DevicePhoneMobileIcon,
  DocumentTextIcon,
  ExclamationTriangleIcon,
  GiftIcon,
  GlobeAltIcon,
  InformationCircleIcon,
  KeyIcon,
  LightBulbIcon,
  ListBulletIcon,
  LockClosedIcon,
  MagnifyingGlassIcon,
  PencilSquareIcon,
  RocketLaunchIcon,
  ShieldCheckIcon,
  SparklesIcon,
  StarIcon,
  UserCircleIcon,
} from '@heroicons/react/24/outline';

// Semantic names keep documentation independent of the underlying icon artwork.
const icons = {
  analytics: ChartBarIcon,
  automation: ArrowPathIcon,
  beelma: SparklesIcon,
  billing: CreditCardIcon,
  business: BriefcaseIcon,
  contact: ChatBubbleLeftRightIcon,
  document: DocumentTextIcon,
  gettingStarted: RocketLaunchIcon,
  google: GlobeAltIcon,
  information: InformationCircleIcon,
  loyalty: GiftIcon,
  mobile: DevicePhoneMobileIcon,
  profile: UserCircleIcon,
  recommendations: LightBulbIcon,
  related: ArrowRightIcon,
  reputation: StarIcon,
  search: MagnifyingGlassIcon,
  security: ShieldCheckIcon,
  signIn: KeyIcon,
  steps: ListBulletIcon,
  success: CheckCircleIcon,
  warning: ExclamationTriangleIcon,
  website: ComputerDesktopIcon,
  writing: PencilSquareIcon,
  alert: BellAlertIcon,
  password: LockClosedIcon,
};

export default function HelpIcon({name, className = ''}) {
  const Icon = icons[name];

  if (!Icon) {
    if (process.env.NODE_ENV !== 'production') {
      console.warn(`Unknown help icon: ${name}`);
    }
    return null;
  }

  return <Icon aria-hidden="true" className={`help-icon help-icon--${name} ${className}`.trim()} focusable="false" />;
}
