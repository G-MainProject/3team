import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import './TopNav.css'
import maleAvatar from '../../assets/images/male.jpg'
import femaleAvatar from '../../assets/images/female.jpg'
import { useAuth } from '../../contexts/AuthContext'

const TopNav = ({ currentPage = 'Dashboard', onStepClick }) => {
  const { user, logout } = useAuth()
  const [currentStep, setCurrentStep] = useState(1) // 현재 진행상황
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const dropdownRef = useRef(null)
  const navigate = useNavigate()
  
  // 사용자 성별 정보 가져오기
  const getUserGender = () => {
    if (!user) return 'male'; // 기본값
    // 서버에서 오는 성별 값: MALE, FEMALE, OTHER
    return user.gender === 'FEMALE' ? 'female' : 'male';
  }
  
  const steps = [
    { id: 1, name: 'START', page: 'START' },
    { id: 2, name: 'RPA', page: 'RPA' },
    { id: 3, name: 'Python', page: 'Python' },
    { id: 4, name: 'Dashboard', page: 'Dashboard' }
  ]

  // 현재 페이지에 따라 진행상황 업데이트
  useEffect(() => {
    const stepIndex = steps.findIndex(step => step.page === currentPage)
    if (stepIndex !== -1) {
      setCurrentStep(stepIndex + 1)
    }
  }, [currentPage, steps])


  // 드롭다운 외부 클릭 시 닫기
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleUserClick = () => {
    setIsDropdownOpen(!isDropdownOpen);
  };

  const handleMyPage = () => {
    setIsDropdownOpen(false);
    // 마이페이지로 이동 (아직 구현되지 않았다면 대시보드로)
    navigate('/dashboard');
  };

  const handleLogout = () => {
    logout();
    setIsDropdownOpen(false);
    alert('로그아웃 되었습니다.');
    navigate('/');
  };

  // 진행상황 클릭 핸들러
  const handleStepClick = (step) => {
    setCurrentStep(step.id)
    if (onStepClick) {
      onStepClick(step.page)
    }
  }

  return (
    <div className='top-nav-container'>
        {/* 진행상황 표시 */}
        <div className='progress-indicator'>
          {steps.map((step, index) => (
            <div key={step.id} className={`progress-step ${currentStep >= step.id ? 'active' : ''}`}>
              <div 
                className={`progress-circle ${currentStep >= step.id ? 'active' : ''}`}
                onClick={() => handleStepClick(step)}
              >
                {step.id}
              </div>
              <span className='progress-label'>{step.name}</span>
              {index < steps.length - 1 && (
                <div className={`progress-line ${currentStep > step.id ? 'active' : ''}`}></div>
              )}
            </div>
          ))}
        </div>

        <button className='top-nav-darkmode'>
            <i className="fa-regular fa-moon fa-flip-horizontal"></i>
        </button>

        <button className='top-nav-bell'>
            <i className="fa-regular fa-bell"></i>
        </button>

        <div className="top-nav-user-container" ref={dropdownRef}>
          <button className="top-nav-user" onClick={handleUserClick}>
              <img src={getUserGender() === 'female' ? femaleAvatar : maleAvatar} alt="avatar" />
              <ul>
                  <li>Welcome back,</li>
                  <li>{user?.name || user?.email || '???'}</li>
              </ul>
              <i className={`fa-solid fa-chevron-down ${isDropdownOpen ? 'rotated' : ''}`}></i>
          </button>
          
          <div className={`top-nav-dropdown ${isDropdownOpen ? 'open' : 'closed'}`}>
            <button className="dropdown-item" onClick={handleMyPage}>
              <i className="fa-solid fa-user"></i>
              <span>마이페이지</span>
            </button>
            <button className="dropdown-item" onClick={handleLogout}>
              <i className="fa-solid fa-arrow-right-from-bracket"></i>
              <span>로그아웃</span>
            </button>
          </div>
        </div>
    </div>
  )
}

export default TopNav
