import React, {forwardRef} from 'react';

function ButtonIcon({Icon, position}) {
  if (!Icon) return null;

  return (
    <Icon
      aria-hidden="true"
      className={`bee-button__icon bee-button__icon--${position}`}
      focusable="false"
    />
  );
}

const BeeButton = forwardRef(function BeeButton(
  {
    children,
    className = '',
    disabled = false,
    href,
    leadingIcon,
    onClick,
    trailingIcon,
    type = 'button',
    variant = 'primary',
    ...props
  },
  ref,
) {
  const classes = `bee-button bee-button--${variant} ${className}`.trim();
  const content = (
    <>
      <ButtonIcon Icon={leadingIcon} position="leading" />
      {children}
      <ButtonIcon Icon={trailingIcon} position="trailing" />
    </>
  );

  if (href) {
    function handleClick(event) {
      if (disabled) {
        event.preventDefault();
        return;
      }
      onClick?.(event);
    }

    return (
      <a
        {...props}
        aria-disabled={disabled || undefined}
        className={classes}
        href={href}
        onClick={handleClick}
        ref={ref}
        tabIndex={disabled ? -1 : props.tabIndex}>
        {content}
      </a>
    );
  }

  return (
    <button {...props} className={classes} disabled={disabled} onClick={onClick} ref={ref} type={type}>
      {content}
    </button>
  );
});

export default BeeButton;
