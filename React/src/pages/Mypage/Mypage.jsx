import React, { useState, useEffect } from 'react';
import styles from './Mypage.module.css';
import logoH from '../../assets/images/logoH.png';
import HomeNav from '../../component/Nav/HomeNav';
import Footer from '../../component/Footer/Footer';
import { useAuth } from '../../contexts/AuthContext';
import apiService from '../../services/api';

const Mypage = () => {
  const { user, updateUser } = useAuth();

  const [name, setName] = useState('');
  const [emailId, setEmailId] = useState('');
  const [emailDomain, setEmailDomain] = useState('');
  const [emailDomainInputDisabled, setEmailDomainInputDisabled] = useState(false);
  const [selectedEmailDomainOption, setSelectedEmailDomainOption] = useState('type');
  const [email, setEmail] = useState('');
  const [id, setId] = useState('');
  const [birthday, setBirthday] = useState('');
  const [gender, setGender] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [passwordConfirmVisible, setPasswordConfirmVisible] = useState(false);
  const [isPasswordVerification, setIsPasswordVerification] = useState(false);
  const [verificationPassword, setVerificationPassword] = useState('');
  const [verificationPasswordVisible, setVerificationPasswordVisible] = useState(false);
  const [isDeleteAccount, setIsDeleteAccount] = useState(false);
  const [deletePassword, setDeletePassword] = useState('');
  const [deletePasswordVisible, setDeletePasswordVisible] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [consentAgreed, setConsentAgreed] = useState(false);


  // 사용자 정보 초기화 (편집 모드가 아닐 때만)
  useEffect(() => {
    if (user && !isEditing) {
      setName(user.name || '');
      setId(user.username || '');
      setBirthday(user.birthDate || '');
      setGender(user.gender === 'FEMALE' ? 'female' : user.gender === 'MALE' ? 'male' : 'other');
      
      // 이메일 분리
      if (user.email) {
        const emailParts = user.email.split('@');
        if (emailParts.length === 2) {
          setEmailId(emailParts[0]);
          setEmailDomain(emailParts[1]);
          setEmail(user.email);
        }
      }
      setConsentAgreed(Boolean(user.consentAgreed));
    }
  }, [user, isEditing]);

  // emailId, emailDomain 바뀔 때 email 상태 업데이트
  useEffect(() => {
    if (emailId && emailDomain) {
      setEmail(`${emailId}@${emailDomain}`);
    } else {
      setEmail('');
    }
  }, [emailId, emailDomain]);

  // 이메일 도메인 select 변경 처리 함수
  const handleEmailDomainChange = e => {
    const val = e.target.value;
    setSelectedEmailDomainOption(val);
    if (val === 'type') {
      setEmailDomain('');
      setEmailDomainInputDisabled(false);
    } else {
      setEmailDomain(val);
      setEmailDomainInputDisabled(true);
    }
  };

  const handleEdit = () => {
    // 다른 모든 상태 초기화
    setIsDeleteAccount(false);
    setIsEditing(false);
    setShowDeleteConfirm(false);
    // 정보수정 패스워드 확인 상태만 활성화
    setIsPasswordVerification(true);
    setError(null);
  };

  const handlePasswordVerification = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    if (!verificationPassword.trim()) {
      setError("비밀번호를 입력해주세요.");
      setLoading(false);
      return;
    }

    try {
      // 패스워드 확인 API 호출
      const response = await apiService.post('/auth/verify-password', {
        emailOrUsername: user.username, // 또는 user.email
        password: verificationPassword
      });
      
      if (response.success && response.data) {
        setIsPasswordVerification(false);
        setIsEditing(true);
        setVerificationPassword('');
      } else {
        setError("비밀번호가 일치하지 않습니다.");
      }
    } catch {
      setError("비밀번호가 일치하지 않습니다.");
    } finally {
      setLoading(false);
    }
  };

  const handleCancelVerification = () => {
    setIsPasswordVerification(false);
    setVerificationPassword('');
    setError(null);
  };

  const handleDeleteAccount = (e) => {
    e.preventDefault();
    e.stopPropagation();
    // 다른 모든 상태 초기화
    setIsPasswordVerification(false);
    setIsEditing(false);
    setShowDeleteConfirm(false);
    // 회원탈퇴 상태만 활성화
    setIsDeleteAccount(true);
    setError(null);
  };

  const handleDeletePasswordVerification = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    if (!deletePassword.trim()) {
      setError("비밀번호를 입력해주세요.");
      setLoading(false);
      return;
    }

    try {
      // 패스워드 확인 API 호출
      const response = await apiService.post('/auth/verify-password', {
        emailOrUsername: user.username,
        password: deletePassword
      });
      
      if (response.success && response.data) {
        setIsDeleteAccount(false);
        setShowDeleteConfirm(true);
        setDeletePassword('');
      } else {
        setError("비밀번호가 일치하지 않습니다.");
        // 패스워드가 틀려도 회원탈퇴 페이지에 머물러야 함
      }
    } catch (err) {
      console.error('패스워드 확인 오류:', err);
      setError("비밀번호 확인 중 오류가 발생했습니다.");
      // 오류가 발생해도 회원탈퇴 페이지에 머물러야 함
    } finally {
      setLoading(false);
    }
  };

  const handleCancelDeleteVerification = () => {
    setIsDeleteAccount(false);
    setDeletePassword('');
    setError(null);
  };

  const handleConfirmDelete = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiService.delete(`/users/${user.id}`);
      
      if (response.success) {
        alert('회원탈퇴가 완료되었습니다.');
        // 로그아웃 처리 (AuthContext에서 로그아웃 함수 호출)
        // updateUser(null) 또는 로그아웃 함수 호출
        window.location.href = '/';
      } else {
        setError(response.message || '회원탈퇴에 실패했습니다.');
      }
    } catch (err) {
      setError(err.response?.data?.message || '회원탈퇴 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
      setShowDeleteConfirm(false);
    }
  };

  const handleCancelDelete = () => {
    setShowDeleteConfirm(false);
    setError(null);
  };

  const handleCancel = () => {
    setIsEditing(false);
    setError(null);
    // 원래 사용자 정보로 복원
    if (user) {
      setName(user.name || '');
      setId(user.username || '');
      setBirthday(user.birthDate || '');
      setGender(user.gender === 'FEMALE' ? 'female' : user.gender === 'MALE' ? 'male' : 'other');
      setPassword('');
      setPasswordConfirm('');
      
      if (user.email) {
        const emailParts = user.email.split('@');
        if (emailParts.length === 2) {
          setEmailId(emailParts[0]);
          setEmailDomain(emailParts[1]);
          setEmail(user.email);
        }
      }
    }
  };


  const handleSave = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    // 필수 필드 검사
    if (!name.trim() || !email.trim() || !birthday.trim() || !gender.trim()) {
      setError("모든 필드를 입력해주세요.");
      setLoading(false);
      return;
    }

    // 비밀번호가 입력된 경우에만 확인 검사
    if (password.trim() && password !== passwordConfirm) {
      setError("비밀번호가 일치하지 않습니다.");
      setLoading(false);
      return;
    }

    // 이메일 유효성 검사
    const emailRegex = /^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}$/;
    if (!emailRegex.test(email)) {
      setError("올바른 이메일 형식이 아닙니다.");
      setLoading(false);
      return;
    }

    try {
      // 성별 값을 서버에서 기대하는 형식으로 변환
      const genderMapping = {
        'male': 'MALE',
        'female': 'FEMALE', 
        'other': 'OTHER'
      };

      const updateData = {
        email: email,
        name: name,
        gender: genderMapping[gender] || 'OTHER',
        birthDate: birthday,
        username: id,
        consentAgreed: consentAgreed
      };

      // 비밀번호가 입력된 경우에만 포함
      if (password.trim()) {
        updateData.password = password;
      }

      const response = await apiService.put(`/users/${user.id}`, updateData);
      
      
      if (response.success) {
        alert('정보가 성공적으로 수정되었습니다!');
        setIsEditing(false);
        
        // AuthContext의 사용자 정보 업데이트
        const updatedUser = {
          ...user,
          name: name,
          email: email,
          gender: genderMapping[gender] || 'OTHER',
          birthDate: birthday,
          username: id,
          consentAgreed: consentAgreed
        };
        updateUser(updatedUser);
      } else {
        setError(response.message || '정보 수정에 실패했습니다.');
      }
    } catch (err) {
      setError(err.response?.data?.message || '정보 수정 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };


  return (
    <div className={styles.mypageContainer}>
      <HomeNav />
      <div className={styles.mypageContent}>
        <form className={styles.mypageForm}>
          <div className={styles.mypageLogo}>
            <img src={logoH} alt="3Team Logo" />
          </div>

          <p>{isDeleteAccount ? '회원탈퇴' : isPasswordVerification ? '비밀번호 확인' : isEditing ? '내 정보 수정' : '내 정보'}</p>
          <h1>{isDeleteAccount ? '회원탈퇴를 위해 비밀번호를 입력해주세요' : isPasswordVerification ? '정보 수정을 위해 비밀번호를 입력해주세요' : '개인정보를 확인하고 수정할 수 있습니다!'}</h1>

          {isDeleteAccount ? (
            <div className={styles.mypageFormGroup}>
              <label htmlFor="deletePassword">현재 비밀번호</label>
              <div className={styles.deletePasswordContainer}>
                <input
                  type={deletePasswordVisible ? 'text' : 'password'}
                  id="deletePassword"
                  className={styles.password}
                  placeholder="현재 비밀번호를 입력하세요"
                  value={deletePassword}
                  onChange={e => setDeletePassword(e.target.value)}
                />
                <i
                  className={`fa ${deletePasswordVisible ? 'fa-eye-slash' : 'fa-eye'} fa-lg`}
                  onClick={() => setDeletePasswordVisible(!deletePasswordVisible)}
                  style={{ cursor: 'pointer' }}
                ></i>
              </div>
              <div className={styles.warningText}>
                ⚠️ 회원탈퇴 시 모든 데이터가 삭제되며 복구할 수 없습니다.
              </div>
            </div>
          ) : isPasswordVerification ? (
            <div className={styles.mypageFormGroup}>
              <label htmlFor="verificationPassword">현재 비밀번호</label>
              <div className={styles.verificationPasswordContainer}>
                <input
                  type={verificationPasswordVisible ? 'text' : 'password'}
                  id="verificationPassword"
                  className={styles.password}
                  placeholder="현재 비밀번호를 입력하세요"
                  value={verificationPassword}
                  onChange={e => setVerificationPassword(e.target.value)}
                />
                <i
                  className={`fa ${verificationPasswordVisible ? 'fa-eye-slash' : 'fa-eye'} fa-lg`}
                  onClick={() => setVerificationPasswordVisible(!verificationPasswordVisible)}
                  style={{ cursor: 'pointer' }}
                ></i>
              </div>
            </div>
          ) : (
            <>
              <div className={styles.mypageFormGroup}>
                <label htmlFor="username">이름</label>
                <input
                  type="text"
                  id="username"
                  placeholder="이름을 입력하세요"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  disabled={!isEditing}
                />
              </div>


              <div className={styles.mypageFormGroup}>
                <label htmlFor="email">이메일</label>
                <div className={styles.emailGroup}>
                  <input
                    type="text"
                    placeholder="이메일 아이디"
                    value={emailId}
                    onChange={e => setEmailId(e.target.value)}
                    disabled={!isEditing}
                  />
                  <p>@</p>
                  <input
                    className="em-box"
                    id="mypage-em-box"
                    type="text"
                    value={emailDomain}
                    disabled={emailDomainInputDisabled || !isEditing}
                    onChange={e => setEmailDomain(e.target.value)}
                  />
                  <select
                    className="em-box"
                    id="mypage-em-list"
                    value={selectedEmailDomainOption}
                    onChange={handleEmailDomainChange}
                    disabled={!isEditing}
                  >
                    <option value="type">직접 입력</option>
                    <option value="naver.com">naver.com</option>
                    <option value="gmail.com">gmail.com</option>
                    <option value="hanmail.net">hanmail.net</option>
                    <option value="nate.com">nate.com</option>
                    <option value="kakao.com">kakao.com</option>
                  </select>
                </div>
              </div>

              <div className={styles.mypageFormGroup}>
                <label htmlFor="id">아이디</label>
                <input
                  type="text"
                  id="id"
                  placeholder="아이디를 입력하세요"
                  value={id}
                  onChange={e => setId(e.target.value)}
                  disabled={true}
                />
                <div className={styles.helpText}>아이디는 변경할 수 없습니다</div>
              </div>

              <div className={styles.mypageFormGroup}>
                <label>성별</label>
                <div className={styles.genderGroup}>
                  <button
                    type="button"
                    className={`${styles.genderButton} ${gender === 'male' ? styles.genderButtonActive : ''}`}
                    onClick={() => isEditing && setGender('male')}
                    disabled={!isEditing}
                  >
                    남성
                  </button>
                  <button
                    type="button"
                    className={`${styles.genderButton} ${gender === 'female' ? styles.genderButtonActive : ''}`}
                    onClick={() => isEditing && setGender('female')}
                    disabled={!isEditing}
                  >
                    여성
                  </button>
                  <button
                    type="button"
                    className={`${styles.genderButton} ${gender === 'other' ? styles.genderButtonActive : ''}`}
                    onClick={() => isEditing && setGender('other')}
                    disabled={!isEditing}
                  >
                    밝히고 싶지 않음
                  </button>
                </div>
              </div>

              <div className={styles.mypageFormGroup}>
                <label htmlFor="birthday">생년월일</label>
                <input
                  type="date"
                  id="birthday"
                  value={birthday}
                  onChange={e => setBirthday(e.target.value)}
                  disabled={!isEditing}
                />
              </div>

              <div className={styles.mypageFormGroup}>
                <input
                  id="consent-agree"
                  type="checkbox"
                  checked={consentAgreed}
                  onChange={e => isEditing && setConsentAgreed(e.target.checked)}
                  disabled={!isEditing}
                />
                <label htmlFor="consent-agree" style={{ cursor: isEditing ? 'pointer' : 'default' }}>
                  마케팅/이벤트 알림 수신에 동의합니다.
                </label>
                {user?.consentAgreedAt && (
                  <div className={styles.helpText}>동의 시각: {new Date(user.consentAgreedAt).toLocaleString()}</div>
                )}
              </div>

              {isEditing && (
                <>
                  <div className={`${styles.mypageFormGroup} ${styles.infoPw}`}>
                    <label htmlFor="password">새 비밀번호</label>
                    <input
                      type={passwordVisible ? 'text' : 'password'}
                      id="password"
                      className={styles.password}
                      placeholder="새 비밀번호를 입력하세요"
                      value={password}
                      onChange={e => setPassword(e.target.value)}
                    />
                    <i
                      className={`fa ${passwordVisible ? 'fa-eye-slash' : 'fa-eye'} fa-lg`}
                      onClick={() => setPasswordVisible(!passwordVisible)}
                      style={{ cursor: 'pointer' }}
                    ></i>
                    <div className={styles.helpText}>비밀번호를 변경하지 않으려면 비워두세요</div>
                  </div>

                  <div className={`${styles.mypageFormGroup} ${styles.infoPwRe}`}>
                    <label htmlFor="passwordConfirm">비밀번호 확인</label>
                    <input
                      id="passwordConfirm"
                      className={styles.passwordRe}
                      type={passwordConfirmVisible ? 'text' : 'password'}
                      placeholder="비밀번호를 다시 입력하세요"
                      value={passwordConfirm}
                      onChange={e => setPasswordConfirm(e.target.value)}
                    />
                    <i
                      className={`fa ${passwordConfirmVisible ? 'fa-eye-slash' : 'fa-eye'} fa-lg`}
                      onClick={() => setPasswordConfirmVisible(!passwordConfirmVisible)}
                      style={{ cursor: 'pointer' }}
                    ></i>
                  </div>
                </>
              )}
            </>
          )}

          {error && (
            <div className={styles.errorMessage}>
              {error}
            </div>
          )}

          <div className={`${styles.mypageFormGroup} ${styles.jcc}`}>
            {isDeleteAccount ? (
              <div className={styles.buttonGroup}>
                <button 
                  type="button" 
                  className={styles.cancelButton} 
                  onClick={handleCancelDeleteVerification}
                >
                  취소
                </button>
                <button 
                  type="submit" 
                  className={styles.deleteButton} 
                  onClick={handleDeletePasswordVerification}
                  disabled={loading}
                >
                  {loading ? '확인 중...' : '확인'}
                </button>
              </div>
            ) : isPasswordVerification ? (
              <div className={styles.buttonGroup}>
                <button 
                  type="button" 
                  className={styles.cancelButton} 
                  onClick={handleCancelVerification}
                >
                  취소
                </button>
                <button 
                  type="submit" 
                  className={styles.saveButton} 
                  onClick={handlePasswordVerification}
                  disabled={loading}
                >
                  {loading ? '확인 중...' : '확인'}
                </button>
              </div>
            ) : !isEditing ? (
              <div className={styles.buttonContainer}>
                <button 
                  type="button" 
                  className={styles.editButton} 
                  onClick={handleEdit}
                >
                  정보 수정
                </button>
                <button 
                  type="button" 
                  className={styles.deleteAccountButton} 
                  onClick={handleDeleteAccount}
                >
                  회원탈퇴
                </button>
              </div>
            ) : (
              <div className={styles.buttonGroup}>
                <button 
                  type="button" 
                  className={styles.cancelButton} 
                  onClick={handleCancel}
                >
                  취소
                </button>
                <button 
                  type="submit" 
                  className={styles.saveButton} 
                  onClick={handleSave}
                  disabled={loading}
                >
                  {loading ? '저장 중...' : '저장'}
                </button>
              </div>
            )}
          </div>

        </form>
      </div>
      
      {/* 회원탈퇴 확인 다이얼로그 */}
      {showDeleteConfirm && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalContent}>
            <h2>회원탈퇴 확인</h2>
            <p>정말로 회원탈퇴를 하시겠습니까?</p>
            <p className={styles.warningText}>
              ⚠️ 회원탈퇴 시 모든 데이터가 삭제되며 복구할 수 없습니다.
            </p>
            <div className={styles.modalButtons}>
              <button 
                className={styles.cancelButton} 
                onClick={handleCancelDelete}
                disabled={loading}
              >
                취소
              </button>
              <button 
                className={styles.deleteButton} 
                onClick={handleConfirmDelete}
                disabled={loading}
              >
                {loading ? '탈퇴 중...' : '탈퇴하기'}
              </button>
            </div>
          </div>
        </div>
      )}
      
      <Footer />
    </div>
  );
};

export default Mypage;