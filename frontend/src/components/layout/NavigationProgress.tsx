import { motion, AnimatePresence } from 'motion/react';
import { useNavigation } from 'react-router-dom';

/** Thin top-of-shell progress bar shown while a lazy route chunk / loader is in flight. */
export function NavigationProgress() {
  const navigation = useNavigation();
  const isLoading = navigation.state !== 'idle';

  return (
    <AnimatePresence>
      {isLoading && (
        <motion.div
          initial={{ scaleX: 0, opacity: 1 }}
          animate={{ scaleX: 0.8, opacity: 1 }}
          exit={{ scaleX: 1, opacity: 0 }}
          transition={{ duration: isLoading ? 0.6 : 0.15 }}
          style={{ transformOrigin: 'left' }}
          className="absolute inset-x-0 top-0 z-50 h-0.5 bg-accent"
          role="status"
          aria-label="Loading page"
        />
      )}
    </AnimatePresence>
  );
}
