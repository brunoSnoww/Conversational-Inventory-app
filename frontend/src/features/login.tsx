import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Box, Button, PasswordInput, SegmentedControl, Stack, TextInput } from '@mantine/core';
import { hasLength, isEmail, isNotEmpty, matchesField, useForm } from '@mantine/form';

import { shellTextureStyle } from '../app/theme';
import { useAuth } from '../auth/AuthContext';
import { routes } from '../routes';
import { ErrorText, Page, friendlyError } from './ui';

type AuthMode = 'signin' | 'signup';

const DEMO_SIGN_IN = {
  email: 'demo@inventory.local',
  password: 'password123',
} as const;

export function LoginPage() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mode, setMode] = useState<AuthMode>('signin');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const signInForm = useForm({
    initialValues: { ...DEMO_SIGN_IN },
    validate: {
      email: isEmail('Invalid email'),
      password: isNotEmpty('Password is required'),
    },
  });

  const signUpForm = useForm({
    initialValues: {
      email: '',
      password: '',
      confirmPassword: '',
    },
    validate: {
      email: isEmail('Invalid email'),
      password: hasLength({ min: 8 }, 'Password must be at least 8 characters'),
      confirmPassword: matchesField('password', 'Passwords do not match'),
    },
  });

  async function afterAuth() {
    const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname;
    navigate(from ?? routes.dashboard, { replace: true });
  }

  return (
    <Box mih="100vh" p="md" style={shellTextureStyle}>
      <Page title={mode === 'signin' ? 'Sign in' : 'Create account'} narrow>
        <SegmentedControl
          fullWidth
          value={mode}
          onChange={(value) => {
            setMode(value as AuthMode);
            setError(null);
          }}
          data={[
            { label: 'Sign in', value: 'signin' },
            { label: 'Create account', value: 'signup' },
          ]}
          mb="md"
        />

        {mode === 'signin' ? (
          <form
            onSubmit={signInForm.onSubmit(async (values) => {
              setLoading(true);
              setError(null);
              try {
                await login(values.email, values.password);
                await afterAuth();
              } catch (err) {
                setError(friendlyError(err));
              } finally {
                setLoading(false);
              }
            })}
          >
            <Stack gap="md">
              <TextInput label="Email" type="email" {...signInForm.getInputProps('email')} />
              <PasswordInput label="Password" {...signInForm.getInputProps('password')} />
              {error && <ErrorText title="Sign in failed">{error}</ErrorText>}
              <Button type="submit" loading={loading}>
                Sign in
              </Button>
            </Stack>
          </form>
        ) : (
          <form
            onSubmit={signUpForm.onSubmit(async (values) => {
              setLoading(true);
              setError(null);
              try {
                await register(values.email, values.password);
                await afterAuth();
              } catch (err) {
                setError(friendlyError(err));
              } finally {
                setLoading(false);
              }
            })}
          >
            <Stack gap="md">
              <TextInput label="Email" type="email" {...signUpForm.getInputProps('email')} />
              <PasswordInput label="Password" {...signUpForm.getInputProps('password')} />
              <PasswordInput
                label="Confirm password"
                {...signUpForm.getInputProps('confirmPassword')}
              />
              {error && <ErrorText title="Registration failed">{error}</ErrorText>}
              <Button type="submit" loading={loading}>
                Create account
              </Button>
            </Stack>
          </form>
        )}
      </Page>
    </Box>
  );
}
